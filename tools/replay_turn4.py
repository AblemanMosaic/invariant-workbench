#!/usr/bin/env python3
"""One local replay: regression/proofs, UCM fixtures, integrations and Foundry.

No package installation, network access, model API or database connection is requested.
This is builder-check reproduction, not an independent review by itself.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/ucm'),str(ROOT/'vendor/mosaic')]
from miw.common import Refusal,require,seal,write_json,BOUNDARY,validate_replay_output
from miw.qualification import source_inventory

COMMAND_TIMEOUT_SECONDS=1200

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True)
    p.add_argument('--include-local-cpp',action='store_true',help='Explicitly compile and execute the builder-authored C++ probe.')
    args=p.parse_args();out=validate_replay_output(ROOT,Path(args.out))
    out.mkdir(parents=True);before=source_inventory(ROOT);commands=[]
    plan=[('qualification','qualify.py',['--out',str(out/'qualification')]),
          ('custody','ucm_custody_tests.py',['--out',str(out/'custody')]),
          ('integration','miw.py',['integration-demo','--out',str(out/'integration')]),
          ('foundry','recompile_ui.py',['--out',str(out/'foundry')]),
          ('headless','miw.py',['headless-ui','--out',str(out/'HEADLESS.json')])]
    if args.include_local_cpp:plan.append(('cpp','miw.py',['cpp-probe','--allow-trusted-compile','--out',str(out/'cpp')]))
    for name,tool,extra in plan:
        argv=[sys.executable,'-I','-B',str(ROOT/'tools'/tool),*extra]
        with (out/(name+'.log')).open('wb') as log:
            try:code=subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=COMMAND_TIMEOUT_SECONDS).returncode
            except subprocess.TimeoutExpired:code=124
        commands.append({'task':name,'returncode':code,'log':name+'.log'})
        print(name+': '+('PASSED_LOCAL_REPLAY' if code==0 else 'FAILED_OR_INCOMPLETE'),flush=True)
        if code!=0:break
    stable=before==source_inventory(ROOT)
    ok=len(commands)==len(plan) and all(c['returncode']==0 for c in commands) and stable
    result=seal({'schema':'miw.local_replay.v1',**BOUNDARY,'status':'PASSED_LOCAL_REPLAY' if ok else 'FAILED_OR_INCOMPLETE',
                 'source_root':before['source_root'],'source_unchanged':stable,'commands':commands,
                 'independent_review':False,'external_acceptance':'NOT_PERFORMED_BY_THIS_COMMAND'})
    write_json(out/'SUMMARY.json',result);print(json.dumps(result,indent=2));return 0 if ok else 1
if __name__=='__main__':
    try:raise SystemExit(main())
    except Refusal as exc:print(json.dumps({'status':'REFUSED','code':exc.code}));raise SystemExit(2)
