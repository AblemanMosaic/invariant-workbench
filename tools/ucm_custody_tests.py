#!/usr/bin/env python3
"""Run unchanged inherited manager/migration tests in an isolated namespace."""
from pathlib import Path
import argparse
import importlib.util
import sys
import types
import unittest
import io
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/ucm'),str(ROOT/'vendor/mosaic')]
from miw.common import require,seal,write_json,BOUNDARY
from miw.qualification import RecordedResult,source_inventory

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out);require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS');out.mkdir(parents=True)
    before=source_inventory(ROOT)
    package=types.ModuleType('tests');package.__path__=[str(ROOT/'vendor/ucm/tests')];sys.modules['tests']=package
    suite=unittest.TestSuite()
    for name in ('test_workbench_manager','test_workbench_migration'):
        path=ROOT/'vendor/ucm/tests'/f'{name}.py'
        spec=importlib.util.spec_from_file_location('tests.'+name,path)
        mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;setattr(package,name,mod);spec.loader.exec_module(mod)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(suite)
    unchanged=before==source_inventory(ROOT)
    status='PASSED' if result.wasSuccessful() and not result.skipped and not result.expectedFailures and unchanged else 'FAILED'
    report=seal({'schema':'miw.inherited_custody_regression.v1',**BOUNDARY,'status':status,'tests_run':result.testsRun,
                 'source_root':before['source_root'],'source_unchanged':unchanged,'failures':len(result.failures),
                 'errors':len(result.errors),'skips':len(result.skipped),'records':result.records,
                 'upstream_source':'UNCHANGED_PINNED_C4_MODULES_AND_TESTS','identity_status':'FIXTURE_ONLY',
                 'review':'BUILDER_REPLAY_NOT_INDEPENDENT_REVIEW'})
    write_json(out/'SUMMARY.json',report);(out/'TESTS.log').write_text(log.getvalue(),encoding='utf-8')
    print(log.getvalue());print(status,result.testsRun)
    return 0 if status=='PASSED' else 1
if __name__=='__main__':raise SystemExit(main())
