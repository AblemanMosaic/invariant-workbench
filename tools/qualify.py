#!/usr/bin/env python3
"""Run the builder qualification against exact source in a new output folder."""
from pathlib import Path
import argparse
import os
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/ucm'),str(ROOT/'vendor/mosaic')]
from miw.common import write_json,Refusal,require,seal
from miw.qualification import host_observation,run_tests,source_inventory
from miw.dossier import generate_demo,verify_dossier

def release_host_observation(report:dict,*,host_os:str|None=None) -> dict:
    """Add an explicit real-versus-simulated Windows console test lane."""
    observed=host_observation(report);observed.pop('observation_root')
    console_test=next((row['outcome'] for row in report.get('records',[])
        if row['id'].endswith('ConstitutionalControlTests.test_headless_runner_suppresses_windows_console')),None)
    actual_os=os.name if host_os is None else host_os
    if console_test!='PASSED':lane='NOT_CLAIMED_AFTER_INCOMPLETE_OR_FAILED_TEST'
    elif actual_os=='nt':lane='SIMULATED_AND_REAL_WINDOWS_CONSTANTS_PASSED'
    else:lane='SIMULATED_WINDOWS_CONSTANTS_PASSED_REAL_CONSTANTS_NOT_RUN'
    observed['schema']='miw.host_observation.v3'
    observed['windows_console_suppression_constant_lane']=lane
    return seal(observed,'observation_root')

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out);require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS');out.mkdir(parents=True)
    report,log=run_tests(ROOT)
    write_json(out/'UNIT-TESTS.json',report);(out/'UNIT-TESTS.log').write_text(log,encoding='utf-8')
    write_json(out/'SOURCE-INVENTORY.json',source_inventory(ROOT))
    write_json(out/'HOST-OBSERVATION.json',release_host_observation(report))
    if report['status']!='PASSED':
        print(log);return 1
    summary=generate_demo(ROOT,out/'demo');checked=verify_dossier(out/'demo')
    write_json(out/'DOSSIER-REPLAY.json',checked)
    print(f"PASS: {report['tests_run']} tests ({report['application_tests']} application + {report['inherited_native_proof_tests']} inherited); {sum(x['native_vc_count'] for x in summary['examples'])} native VCs; {len(summary['mutations'])} reproduced mutations.")
    return 0
if __name__=='__main__':raise SystemExit(main())
