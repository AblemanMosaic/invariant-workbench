import importlib.util
import json
import unittest

from helpers import ROOT
from miw.common import check_seal
from miw.qualification import host_observation

spec=importlib.util.spec_from_file_location('miw_qualify_tool',ROOT/'tools/qualify.py')
qualify_tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(qualify_tool)


class HostObservationTests(unittest.TestCase):
    def report(self,status='PASSED'):
        return {'status':status,'source_root':'1'*64,'tests_run':17,'records':[
            {'id':'test_constitutional_control.ConstitutionalControlTests.test_headless_runner_suppresses_windows_console','outcome':'PASSED'}]}

    def test_windows_regression_is_distinct_from_gui_and_visual_studio(self):
        record=check_seal(host_observation(self.report(),os_name='nt',
            platform_value='Windows-test',python_value='Python-test'),'observation_root')
        self.assertEqual(record['local_python_regression'],'PASSED')
        self.assertEqual(record['windows_local_python_regression'],'PASSED')
        self.assertEqual(record['native_windows_gui_acceptance'],'NOT_RUN_BY_QUALIFICATION')
        self.assertEqual(record['windows_visual_studio_zucchini_replay'],'NOT_RUN_BY_QUALIFICATION')
        self.assertNotIn('windows_execution',record)

    def test_non_windows_local_pass_does_not_claim_windows_execution(self):
        record=host_observation(self.report(),os_name='posix',platform_value='Linux-test',python_value='Python-test')
        self.assertEqual(record['local_python_regression'],'PASSED')
        self.assertEqual(record['windows_local_python_regression'],'NOT_RUN_ON_THIS_HOST')

    def test_windows_tool_observation_names_real_constant_lane(self):
        record=qualify_tool.release_host_observation(self.report(),host_os='nt')
        self.assertEqual(record['windows_console_suppression_constant_lane'],
                         'SIMULATED_AND_REAL_WINDOWS_CONSTANTS_PASSED')

    def test_linux_tool_observation_names_simulated_constant_lane(self):
        record=qualify_tool.release_host_observation(self.report(),host_os='posix')
        self.assertEqual(record['windows_console_suppression_constant_lane'],
                         'SIMULATED_WINDOWS_CONSTANTS_PASSED_REAL_CONSTANTS_NOT_RUN')


class CurrentGateRegisterTests(unittest.TestCase):
    def test_zucchini_gate_is_exactly_scoped_and_history_is_preserved(self):
        current=json.loads((ROOT/'evidence/EXTERNAL-GATES.json').read_text(encoding='utf-8'))
        gate=next(item for item in current['gates'] if item['id']=='UPSTREAM_ZUCCHINI')
        self.assertEqual(gate['status'],'PASSED_PINNED_SCOPE')
        self.assertEqual(gate['accepted_scope']['commit'],'e8595c9ae94e45c1e28a3effeb7555725c3ac741')
        self.assertEqual(gate['accepted_scope']['successful_discovery_reports'],19)
        self.assertEqual(gate['accepted_scope']['diagnostic_discovery_failure_reports'],16)
        self.assertIn('later revisions',gate['scope_ceiling'])
        prior=json.loads((ROOT/'evidence/lineage/pre-portability-cleanup/EXTERNAL-GATES.json').read_text(encoding='utf-8'))
        old=next(item for item in prior['gates'] if item['id']=='UPSTREAM_ZUCCHINI')
        self.assertEqual(old['status'],'NOT_RUN')

    def test_windows_gates_keep_three_execution_scopes_separate(self):
        current=json.loads((ROOT/'evidence/EXTERNAL-GATES.json').read_text(encoding='utf-8'))
        gates={item['id']:item for item in current['gates']}
        self.assertEqual(gates['WINDOWS_CONSOLIDATED_REPLAY']['status'],'PASSED')
        self.assertEqual(gates['WINDOWS_NATIVE']['status'],'NOT_RUN')
        self.assertEqual(gates['WINDOWS_ZUCCHINI_VISUAL_STUDIO']['status'],'NOT_RUN')
