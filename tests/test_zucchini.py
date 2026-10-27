import unittest
from copy import deepcopy
from unittest.mock import patch
from miw.common import Refusal
from miw.zucchini import import_report,link_junit,make_junit_binding,parse_junit,validate_report
from helpers import report,report_bytes,junit_bytes,raw

class ZucchiniTests(unittest.TestCase):
    def test_valid_fixture_keeps_evidence_classes_separate(self):
        r=import_report(report_bytes())
        self.assertEqual(r['source_execution'],'NONE')
        self.assertTrue(all(q['proof_status']=='NOT_PROVED' and q['execution_status']=='NOT_IMPORTED' for q in r['requirements']))
    def test_unknown_fields_preserved(self):
        r=report();r['future_addition']={'nested':['kept']};out=import_report(raw(r))
        self.assertEqual(out['raw_report']['future_addition'],r['future_addition'])
    def test_report_paths_never_followed(self):
        r=report();r['sources']={'/private/nonexistent/secret':['not opened']};r['feature_directory']='../../never_opened'
        with patch('builtins.open',side_effect=AssertionError('file read forbidden')):
            out=import_report(raw(r))
        self.assertEqual(out['source_execution'],'NONE')
    def test_empty_failed_discovery_not_success(self):
        r=report();r.update(discovery_success=False,scenarios=[],rules=[])
        out=import_report(raw(r));self.assertFalse(out['discovery_success']);self.assertEqual(out['requirements'],[])
    def test_rejected_scenario_coverage_not_counted(self):
        r=report();r['scenarios'][0]['accepted']=False
        for e in r['rules'][0]['events']:
            if e['scenario_id']==0:e['scenario_accepted']=False
        out=import_report(raw(r));self.assertNotIn(0,out['requirements'][0]['covered_scenarios'])
    def test_uncovered_requirement_preserved(self):
        r=import_report(report_bytes());self.assertEqual(r['requirements'][2]['covered_scenarios'],[])
    def test_junit_link_has_no_requirement_failure_inference(self):
        a,b=report_bytes(),junit_bytes();out=link_junit(a,b,make_junit_binding(a,b))
        self.assertEqual(out['scenario_runs'][0]['status'],'FAILED')
        self.assertEqual(out['failure_attribution'],'NOT_ESTABLISHED')
        self.assertTrue(all(q['counterexample_status']=='NOT_ESTABLISHED_FROM_SCENARIO_STATUS' for q in out['requirements']))
    def test_junit_binding_not_authentication(self):
        a,b=report_bytes(),junit_bytes();binding=make_junit_binding(a,b)
        self.assertEqual(binding['association'],'CALLER_ASSERTED_SAME_BUILD_NOT_ATTESTED')
    def test_missing_execution_is_not_pass(self):
        a=report_bytes();b=b'<testsuite><testcase name="Inventory.0"/></testsuite>'
        r=link_junit(a,b,make_junit_binding(a,b))
        self.assertEqual(r['scenario_runs'][1]['status'],'NOT_RUN')
    def test_junit_skip_not_pass(self):
        a,b=report_bytes(),junit_bytes();r=link_junit(a,b,make_junit_binding(a,b))
        self.assertEqual(r['scenario_runs'][2]['status'],'SKIPPED')
    def test_real_ctest_parameterized_name_links_by_fixture_and_base_name(self):
        report_value=report();scenario=report_value['scenarios'][0]
        name=f"{report_value['fixture']}.{scenario['test_name']}  # GetParam() = {scenario['test_name']}"
        a=raw(report_value);b=f'<testsuite><testcase name="{name}"/></testsuite>'.encode()
        linked=link_junit(a,b,make_junit_binding(a,b))
        self.assertEqual(linked['scenario_runs'][0]['status'],'PASSED')
        self.assertEqual(linked['scenario_runs'][0]['junit_test_name'],name)
    def test_ambiguous_bare_and_fixture_prefixed_junit_names_refuse(self):
        report_value=report();scenario=report_value['scenarios'][0];a=raw(report_value)
        b=(f'<testsuite><testcase name="{scenario["test_name"]}"/>'
           f'<testcase name="{report_value["fixture"]}.{scenario["test_name"]}"/></testsuite>').encode()
        with self.assertRaises(Refusal):link_junit(a,b,make_junit_binding(a,b))
    def test_unmatched_test_not_silently_associated(self):
        a=report_bytes();b=b'<testsuite><testcase name="Other.Inventory.0"/></testsuite>'
        r=link_junit(a,b,make_junit_binding(a,b))
        self.assertEqual(r['unmatched_junit_tests'],['Other.Inventory.0'])
        self.assertTrue(all(s['status']=='NOT_RUN' for s in r['scenario_runs']))
    def test_changed_report_requires_new_binding(self):
        a,b=report_bytes(),junit_bytes();binding=make_junit_binding(a,b)
        with self.assertRaises(Refusal):link_junit(a+b' ',b,binding)
    def test_changed_junit_requires_new_binding(self):
        a,b=report_bytes(),junit_bytes();binding=make_junit_binding(a,b)
        with self.assertRaises(Refusal):link_junit(a,b+b' ',binding)
    def test_wrong_build_rejected(self):
        a,b=report_bytes(),junit_bytes();binding=make_junit_binding(a,b);binding['build_id']='OTHER'
        with self.assertRaises(Refusal):link_junit(a,b,binding)
    def test_no_remote_schema_fetch(self):
        r=report();r['$schema']='https://invalid.example/evil'
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_bool_is_not_scenario_id(self):
        r=report();r['scenarios'][0]['id']=False
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_cross_requirement_unknown(self):
        r=report();r['rules'][0]['events'][0]['tag']='invented'
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_cross_scenario_unknown(self):
        r=report();r['rules'][0]['events'][0]['scenario_id']=42
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_cross_scenario_identity_mismatch(self):
        r=report();r['rules'][0]['events'][0]['test_name']='Different'
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_upstream_numbered_duplicate_scenario_display_name_is_supported(self):
        r=report();r['scenarios'][0]['name']+=' #2'
        self.assertEqual(import_report(raw(r))['fixture'],r['fixture'])
    def test_non_upstream_duplicate_name_suffix_refuses(self):
        r=report();r['scenarios'][0]['name']+=' #1'
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_coverage_assertion_must_resolve(self):
        r=report();r['rules'][0]['events'][0]['line']=999
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_coverage_cell_must_resolve(self):
        r=report();r['rules'][0]['events'][0]['cell']={'row':0,'key':'invented'}
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_resolved_cell_is_supported(self):
        r=report();s=r['scenarios'][0]['steps'][-1]
        s['argument']={'kind':'dataTable','rows':[{'count':'0'}]}
        r['rules'][0]['events'][0]['cell']={'row':0,'key':'count'}
        self.assertEqual(import_report(raw(r))['fixture'],'Inventory')
    def test_duplicate_scenario_id(self):
        r=report();r['scenarios'][1]['id']=0
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_duplicate_test_name(self):
        r=report();r['scenarios'][1]['test_name']=r['scenarios'][0]['test_name']
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_duplicate_json_keys(self):
        with self.assertRaises(Refusal):import_report(b'{"schema_version":"2.2.0","schema_version":"3.0.0"}')
    def test_nonfinite_json_refused(self):
        with self.assertRaises(Refusal):import_report(b'{"x":NaN}')
    def test_floats_in_uninterpreted_json_refused(self):
        r=report();r['new_float']=1.5
        with self.assertRaises(Refusal):import_report(raw(r))
    def test_no_boolean_success_from_empty_xml(self):
        with self.assertRaises(Refusal):parse_junit(b'<testsuite/>')
    def test_duplicate_xml_tests_refused(self):
        with self.assertRaises(Refusal):parse_junit(b'<testsuite><testcase name="x"/><testcase name="x"/></testsuite>')
    def test_failed_and_skipped_refused(self):
        with self.assertRaises(Refusal):parse_junit(b'<testsuite><testcase name="x"><failure/><skipped/></testcase></testsuite>')
    def test_dtd_refused(self):
        with self.assertRaises(Refusal):parse_junit(b'<!DOCTYPE x [<!ENTITY x "bad">]><testsuite><testcase name="x"/></testsuite>')
    def test_utf16_entity_bypass_refused(self):
        x='<!DOCTYPE x [<!ENTITY x "bad">]><testsuite><testcase name="x"/></testsuite>'
        with self.assertRaises(Refusal):parse_junit(x.encode('utf-16'))
    def test_xml_error_counted_as_failure(self):
        r=parse_junit(b'<testsuite><testcase name="x"><error/></testcase></testsuite>')
        self.assertEqual(r['tests']['x']['status'],'FAILED')
    def test_xml_notrun_is_not_pass(self):
        r=parse_junit(b'<testsuite><testcase name="x" status="notrun"/></testsuite>')
        self.assertEqual(r['tests']['x']['status'],'NOT_RUN')

for version in ['2.0.0','2.1.0','2.2','2.2.0-beta','2.2.0+build','3.0.0','',2,True,None]:
    def case(self,version=version):
        r=report();r['schema_version']=version
        with self.assertRaises(Refusal):import_report(raw(r))
    setattr(ZucchiniTests,'test_version_refused_'+str(version).replace('.','_').replace('+','_').replace('-','_'),case)
for field in ['fixture','rules','scenarios','discovery_id','discovery_success','sources']:
    def case(self,field=field):
        r=report();del r[field]
        with self.assertRaises(Refusal):import_report(raw(r))
    setattr(ZucchiniTests,'test_missing_'+field,case)
