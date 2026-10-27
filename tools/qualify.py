#!/usr/bin/env python3
"""Run the builder qualification against exact source in a new output folder."""
from pathlib import Path
import argparse
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/ucm'),str(ROOT/'vendor/mosaic')]
from miw.common import write_json,Refusal,require
from miw.qualification import host_observation,run_tests,source_inventory
from miw.dossier import generate_demo,verify_dossier

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out);require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS');out.mkdir(parents=True)
    report,log=run_tests(ROOT)
    write_json(out/'UNIT-TESTS.json',report);(out/'UNIT-TESTS.log').write_text(log,encoding='utf-8')
    write_json(out/'SOURCE-INVENTORY.json',source_inventory(ROOT))
    write_json(out/'HOST-OBSERVATION.json',host_observation(report))
    if report['status']!='PASSED':
        print(log);return 1
    summary=generate_demo(ROOT,out/'demo');checked=verify_dossier(out/'demo')
    write_json(out/'DOSSIER-REPLAY.json',checked)
    print(f"PASS: {report['tests_run']} tests ({report['application_tests']} application + {report['inherited_native_proof_tests']} inherited); {sum(x['native_vc_count'] for x in summary['examples'])} native VCs; {len(summary['mutations'])} reproduced mutations.")
    return 0
if __name__=='__main__':raise SystemExit(main())
