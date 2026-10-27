#!/usr/bin/env python3
"""Explicitly replay the builder challenges against the exact preserved predecessor.

Executes known predecessor code locally. Not an OS sandbox or independent review.
The source archive is fixed, hash-pinned and byte-verified before extraction.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import subprocess
import sys
import zipfile
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/ucm'),str(ROOT/'vendor/mosaic')]
from miw.common import Refusal,validate_replay_output
PIN='bedce795797dbb2f170aa293c60fea19f371bc34f41440e1f6ea8eba860b9ef7'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-reviewed-subject',action='store_true')
    parser.add_argument('--out',required=True);args=parser.parse_args()
    if not args.allow_reviewed_subject:
        parser.error('Explicit --allow-reviewed-subject is required.')
    out=validate_replay_output(ROOT,Path(args.out))
    spec=importlib.util.spec_from_file_location('miw_prior_verifier',ROOT/'VERIFY.py')
    verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
    archive=ROOT/'history/turn3/FROZEN-CANDIDATE.zip';verified=verifier.verify(archive,PIN)
    out.mkdir(parents=True);subject=out/'subject';subject.mkdir()
    with zipfile.ZipFile(archive) as z:z.extractall(subject)
    worker=out/'challenge.py';worker.write_bytes((ROOT/'fixtures/turn3_challenge.py.txt').read_bytes())
    (out/'VERIFIED-PREDECESSOR.json').write_text(json.dumps(verified,indent=2)+'\n')
    with (out/'CHALLENGE.log').open('wb') as log:
        done=subprocess.run([sys.executable,'-I','-B',str(worker),str(subject),str(out)],stdout=log,stderr=subprocess.STDOUT,timeout=300)
    print(json.dumps({'status':'OBSERVED_PREDECESSOR_FINDINGS' if done.returncode==0 else 'REPLAY_FAILED',
                      'returncode':done.returncode,'subject_sha256':PIN,'output':str(out),
                      'independent_review':False,'production_authority':False},indent=2))
    return done.returncode
if __name__=='__main__':
    try:raise SystemExit(main())
    except Refusal as exc:print(json.dumps({'status':'REFUSED','code':exc.code}));raise SystemExit(2)
