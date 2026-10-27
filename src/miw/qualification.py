"""Measured unittest runs. These are builder tests, not independent review."""
from __future__ import annotations
from pathlib import Path
import importlib.util
import io
import os
import platform
import sys
import time
import unittest
from .common import BOUNDARY,seal,digest,read_bytes

class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.records=[]
    def startTest(self,test):
        super().startTest(test)
        if os.environ.get('MIW_PROGRESS')=='1':print('RUN '+test.id(),file=sys.stderr,flush=True)
    def addSuccess(self,test):super().addSuccess(test);self.records.append({'id':test.id(),'outcome':'PASSED'})
    def addFailure(self,test,err):super().addFailure(test,err);self.records.append({'id':test.id(),'outcome':'FAILED'})
    def addError(self,test,err):super().addError(test,err);self.records.append({'id':test.id(),'outcome':'ERROR'})
    def addSkip(self,test,reason):super().addSkip(test,reason);self.records.append({'id':test.id(),'outcome':'SKIPPED','reason':reason})
    def addExpectedFailure(self,test,err):super().addExpectedFailure(test,err);self.records.append({'id':test.id(),'outcome':'EXPECTED_FAILURE'})
    def addUnexpectedSuccess(self,test):super().addUnexpectedSuccess(test);self.records.append({'id':test.id(),'outcome':'UNEXPECTED_SUCCESS'})

def source_inventory(project:Path) -> dict:
    rows=[]
    # Path ordering follows host path semantics (case folding on Windows), so it
    # cannot be part of a cross-platform canonical root. Sort by the canonical
    # POSIX relative path that is actually sealed into the inventory instead.
    paths=sorted(project.rglob('*'),key=lambda p:p.relative_to(project).as_posix())
    for p in paths:
        rel=p.relative_to(project).as_posix()
        if not p.is_file() or rel.startswith('evidence/') or rel in {'MANIFEST.json','SHA256SUMS'}:continue
        if '__pycache__' in p.parts or p.suffix=='.pyc':continue
        rows.append({'path':rel,'sha256':digest(read_bytes(p)),'bytes':p.stat().st_size})
    return seal({'schema':'miw.source_inventory.v1','files':rows},'source_root')

def host_observation(test_report:dict,*,os_name:str|None=None,platform_value:str|None=None,
                     python_value:str|None=None) -> dict:
    """Describe local regression and still-open Windows lanes independently."""
    host_os=os.name if os_name is None else os_name
    local_status=test_report['status']
    if host_os=='nt':windows_regression='PASSED' if local_status=='PASSED' else 'FAILED'
    else:windows_regression='NOT_RUN_ON_THIS_HOST'
    return seal({'schema':'miw.host_observation.v2',**BOUNDARY,
        'python':sys.version if python_value is None else python_value,
        'platform':platform.platform() if platform_value is None else platform_value,
        'role':'OBSERVATION_ONLY','source_root':test_report['source_root'],
        'tests_run':test_report['tests_run'],'local_python_regression':local_status,
        'windows_local_python_regression':windows_regression,
        'native_windows_gui_acceptance':'NOT_RUN_BY_QUALIFICATION',
        'windows_visual_studio_zucchini_replay':'NOT_RUN_BY_QUALIFICATION',
        'independent_review':'NOT_PERFORMED'},'observation_root')

def run_tests(project:Path) -> tuple[dict,str]:
    before=source_inventory(project);start=time.monotonic()
    sys.dont_write_bytecode=True
    if str(project/'tests') not in sys.path:sys.path.insert(0,str(project/'tests'))
    app=unittest.defaultTestLoader.discover(str(project/'tests'),pattern='test_*.py')
    path=project/'vendor/ucm/tests/test_deductive_proofs.py'
    spec=importlib.util.spec_from_file_location('ucm_inherited_native_tests',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    inherited=unittest.defaultTestLoader.loadTestsFromModule(module)
    app_count=app.countTestCases();inherited_count=inherited.countTestCases()
    suite=unittest.TestSuite([app,inherited]);log=io.StringIO()
    result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(suite)
    after=source_inventory(project)
    passed=result.wasSuccessful() and not result.skipped and not result.expectedFailures and before==after
    report=seal({'schema':'miw.test_qualification.v1',**BOUNDARY,'status':'PASSED' if passed else 'FAILED',
        'source_root':before['source_root'],'source_unchanged':before==after,'tests_run':result.testsRun,
        'application_tests':app_count,'inherited_native_proof_tests':inherited_count,
        'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
        'expected_failures':len(result.expectedFailures),'unexpected_successes':len(result.unexpectedSuccesses),
        'records':result.records,'review_class':'BUILDER_AUTHORED_REGRESSION_NOT_INDEPENDENT_REVIEW'},'qualification_root')
    return report,log.getvalue()
