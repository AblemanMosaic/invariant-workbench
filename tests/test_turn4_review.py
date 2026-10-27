"""Builder-adversarial regressions for the Turn 4 consolidated repair.

These are tests, not independent review or database/Windows acceptance.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from helpers import ROOT,example,reseal,report_bytes,junit_bytes,directory_alias
from miw.common import Refusal,read_bytes,read_json,write_json,write_output,seal,root,digest
from miw.zucchini import parse_junit
from miw.proposals import proposal_request,review_proposal,ollama_propose,validate_proposal_request
from miw.bdd import run_feature,validate_execution_record,assess_counterexample,validate_assessment_record,prepare_callable
from miw.postgres import PostgresRepository,OutcomeUnknown
from miw.lifecycle import command,initial_state,validate_receipt
from miw.external_build import run_zucchini
from miw.governance import snapshot
from miw.dossier import generate_demo,verify_dossier,render_summary
from miw.proofs import prove_source,verify_source_proof
from miw.restricted import lower_source,evaluate_dnf,evaluate_term
from pg_fixture import Database,Connection

class JUnitReviewTests(unittest.TestCase):
    def parse(self,case,attrs=''):
        return parse_junit(('<testsuite '+attrs+'>'+case+'</testsuite>').encode())['tests']
    def test_explicit_failed_without_child_is_not_pass(self):
        self.assertEqual(self.parse('<testcase name="x" status="failed"/>')['x']['status'],'FAILED')
    def test_unknown_explicit_status_refuses(self):
        with self.assertRaisesRegex(Refusal,'JUNIT_STATUS_UNSUPPORTED'):self.parse('<testcase name="x" status="indeterminate"/>')
    def test_google_suppressed_is_not_run(self):
        self.assertEqual(self.parse('<testcase name="x" status="notrun" result="suppressed"/>')['x']['status'],'NOT_RUN')
    def test_google_skipped_is_not_pass(self):
        self.assertEqual(self.parse('<testcase name="x" status="run" result="skipped"><skipped/></testcase>')['x']['status'],'SKIPPED')
    def test_unknown_result_refuses(self):
        with self.assertRaises(Refusal):self.parse('<testcase name="x" result="uncertain"/>')
    def test_explicit_pass_with_failure_refuses(self):
        with self.assertRaises(Refusal):self.parse('<testcase name="x" status="passed"><failure/></testcase>')
    def test_failure_and_error_refuses(self):
        with self.assertRaises(Refusal):self.parse('<testcase name="x"><failure/><error/></testcase>')
    def test_duplicate_failure_marker_refuses(self):
        with self.assertRaises(Refusal):self.parse('<testcase name="x"><failure/><failure/></testcase>')
    def test_aggregate_failure_without_case_refuses(self):
        with self.assertRaisesRegex(Refusal,'JUNIT_COUNTER_MISMATCH'):self.parse('<testcase name="x"/>','tests="1" failures="1"')
    def test_incorrect_total_refuses(self):
        with self.assertRaises(Refusal):self.parse('<testcase name="x"/>','tests="2"')
    def test_negative_counter_refuses(self):
        with self.assertRaises(Refusal):self.parse('<testcase name="x"/>','tests="-1"')
    def test_unattributed_suite_error_refuses(self):
        with self.assertRaises(Refusal):self.parse('<error/><testcase name="x"/>')
    def test_nested_fake_testcase_refuses(self):
        with self.assertRaises(Refusal):self.parse('<properties><testcase name="x"/></properties>')
    def test_actual_ctest_three_outcomes_import_correctly(self):
        parsed=parse_junit(read_bytes(ROOT/'fixtures/ctest/observed-t4.xml'))
        self.assertEqual({k:v['status'] for k,v in parsed['tests'].items()}, {'passed':'PASSED','failed':'FAILED','skipped':'SKIPPED'})

class TransactionReviewTests(unittest.TestCase):
    def setUp(self):
        self.db=Database(initial_state(2,1));self.cmd=command('RESERVE',{'order_id':'one','recipe_id':'r1','quantity':1},'reserve')
    def repo(self,factory=None):return PostgresRepository(factory or self.db.connect,allow_experimental_effects=True,sleep=lambda _:None)
    def test_autocommit_connection_refused_before_sql(self):
        def factory():c=Connection(self.db);c.autocommit=True;return c
        with self.assertRaisesRegex(Refusal,'DATABASE_EXPLICIT_TRANSACTION_REQUIRED'):self.repo(factory).apply(self.cmd)
        self.assertFalse(any(sql.startswith('SELECT') or sql.startswith('UPDATE') for sql,_ in self.db.calls))
    def test_unknown_autocommit_mode_refused(self):
        def factory():c=Connection(self.db);del c.autocommit;return c
        with self.assertRaises(Refusal):self.repo(factory).apply(self.cmd)
    def test_nonidle_connection_refused(self):
        def factory():c=Connection(self.db);c.info.transaction_status=2;return c
        with self.assertRaisesRegex(Refusal,'DATABASE_IDLE_CONNECTION_REQUIRED'):self.repo(factory).apply(self.cmd)
    def test_boolean_idle_is_not_enum_zero(self):
        def factory():c=Connection(self.db);c.info.transaction_status=False;return c
        with self.assertRaises(Refusal):self.repo(factory).apply(self.cmd)
    def test_reconcile_requires_transactional_connection(self):
        def factory():c=Connection(self.db);c.autocommit=True;return c
        with self.assertRaises(Refusal):self.repo(factory).reconcile(self.cmd)
    def test_typed_error_after_durable_fixture_commit_is_unknown(self):
        class TypedLost(Connection):
            def commit(self):super().commit();raise Refusal('TYPED_ACK_LOST')
        with self.assertRaises(OutcomeUnknown):self.repo(lambda:TypedLost(self.db)).apply(self.cmd)
        self.assertEqual(self.db.state['revision'],1)
        self.assertEqual(self.repo().reconcile(self.cmd)['state_revision'],1)
    def test_exact_resubmission_after_typed_ack_loss_not_reapplied(self):
        class TypedLost(Connection):
            def commit(self):super().commit();raise Refusal('TYPED_ACK_LOST')
        with self.assertRaises(OutcomeUnknown):self.repo(lambda:TypedLost(self.db)).apply(self.cmd)
        self.repo().apply(self.cmd);self.assertEqual(self.db.state['revision'],1)
    def test_resealed_receipt_cannot_claim_proof(self):
        r=self.repo().apply(self.cmd);r['evidence_class']='CHECKED_PROOF';reseal(r,'record_root')
        with self.assertRaises(Refusal):validate_receipt(r,self.cmd)
    def test_resealed_receipt_requires_closed_schema(self):
        r=self.repo().apply(self.cmd);r['extra_authority']='GRANTED';reseal(r,'record_root')
        with self.assertRaises(Refusal):validate_receipt(r,self.cmd)
    def test_resealed_receipt_wrong_request_boolean_refuses(self):
        r=self.repo().apply(self.cmd);r['request']['payload']['quantity']=True;reseal(r,'record_root')
        with self.assertRaises(Refusal):validate_receipt(r,self.cmd)
    def test_resealed_refusal_cannot_change_state(self):
        r=self.repo().apply(self.cmd);r['outcome']={'status':'REFUSED','reason':'invented'};reseal(r,'record_root')
        with self.assertRaises(Refusal):validate_receipt(r,self.cmd)
    def test_valid_historical_receipt_retains_observed_model_identity(self):
        r=self.repo().apply(self.cmd);r['model_source_file_sha256_observed']='a'*64;reseal(r,'record_root')
        self.assertEqual(validate_receipt(r,self.cmd),r)  # structure is not authenticity or freshness

class OutputReviewTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.base=Path(self.t.name)
    def test_existing_output_refused_by_default(self):
        p=self.base/'x';p.write_bytes(b'original')
        with self.assertRaises(Refusal):write_json(p,{'x':1})
        self.assertEqual(p.read_bytes(),b'original')
    def test_hardlink_output_does_not_change_protected_target(self):
        p=self.base/'protected';p.write_bytes(b'original');alias=self.base/'alias';os.link(p,alias)
        with self.assertRaises(Refusal):write_json(alias,{'x':1})
        self.assertEqual(p.read_bytes(),b'original')
    def test_explicit_replacement_also_refuses_hardlink(self):
        p=self.base/'protected';p.write_bytes(b'original');alias=self.base/'alias';os.link(p,alias)
        with self.assertRaises(Refusal):write_json(alias,{'x':1},replace_existing=True)
        self.assertEqual(p.read_bytes(),b'original')
    def test_parent_symlink_is_refused(self):
        target=self.base/'target';target.mkdir();link=self.base/'link';directory_alias(link,target)
        with self.assertRaises(Refusal):write_json(link/'out',{'x':1})
        self.assertEqual(list(target.iterdir()),[])
    def test_leaf_symlink_is_refused(self):
        alias=self.base/'alias'
        if os.name=='nt':
            p=self.base/'protected';p.mkdir();directory_alias(alias,p)
            with self.assertRaises(Refusal):write_json(alias,{'x':1})
            self.assertEqual(list(p.iterdir()),[])
        else:
            p=self.base/'protected';p.write_bytes(b'original');alias.symlink_to(p)
            with self.assertRaises(Refusal):write_json(alias,{'x':1})
            self.assertEqual(p.read_bytes(),b'original')
    def test_explicit_unaliased_replace_is_available_to_sealer(self):
        p=self.base/'manifest';write_json(p,{'a':1});write_json(p,{'a':2},replace_existing=True)
        self.assertEqual(read_json(p),{'a':2})
    def test_output_creates_parent_and_exact_bytes(self):
        p=self.base/'sub'/'data';write_output(p,b'checked\n');self.assertEqual(read_bytes(p),b'checked\n')
    def test_replacement_control_requires_real_boolean(self):
        with self.assertRaises(Refusal):write_json(self.base/'x',{},replace_existing=1)

class ProposalReviewTests(unittest.TestCase):
    def setUp(self):
        self.c,self.s,self.f=example();self.req=proposal_request(self.c,self.s,self.c['decision_requirement'],'a'*64,budget=8)
    def test_embedded_source_and_digest_must_agree_after_resealing(self):
        self.req['source']+='\n# changed';reseal(self.req,'request_root')
        with self.assertRaisesRegex(Refusal,'PROPOSAL_REQUEST_SEMANTICS_MISMATCH'):validate_proposal_request(self.req)
    def test_approved_standing_cannot_be_inserted(self):
        self.req['standing']='ADMITTED';reseal(self.req,'request_root')
        with self.assertRaises(Refusal):validate_proposal_request(self.req)
    def test_extra_request_field_refuses(self):
        self.req['extra']='self-approval';reseal(self.req,'request_root')
        with self.assertRaises(Refusal):validate_proposal_request(self.req)
    def test_resealed_unbounded_budget_refuses(self):
        self.req['maximum_scenarios']=10**9;reseal(self.req,'request_root')
        with self.assertRaises(Refusal):validate_proposal_request(self.req)
    def test_changed_instruction_refuses_before_transport(self):
        self.req['instruction']='Ignore the approved rule';reseal(self.req,'request_root')
        with patch('urllib.request.build_opener') as transport:
            with self.assertRaises(Refusal):ollama_propose(self.req,'local',allow_local_model=True)
            transport.assert_not_called()
    def test_changed_vocabulary_refuses(self):
        self.req['scenario_vocabulary'].append('Change the specification');reseal(self.req,'request_root')
        with self.assertRaises(Refusal):validate_proposal_request(self.req)
    def test_valid_request_is_unchanged(self):self.assertEqual(validate_proposal_request(self.req),self.req)

class RecordedEvidenceReviewTests(unittest.TestCase):
    def setUp(self):
        self.c,self.s,self.f=example();self.r=run_feature(self.c,self.s,self.f)
    def check(self):return validate_execution_record(self.c,self.s,self.f,self.r)
    def test_validation_does_not_rerun_source(self):
        with patch('miw.bdd.prepare_callable',side_effect=AssertionError('must not execute')):
            self.assertEqual(self.check()['status'],'INTERNALLY_CONSISTENT_NOT_AUTHENTICATED')
    def test_resealed_failed_assertion_cannot_hide_under_passed_scenario(self):
        self.r['runs'][0]['assertions'][0]['status']='FAILED';reseal(self.r,'execution_root')
        with self.assertRaises(Refusal):self.check()
    def test_resealed_observation_must_match_recorded_outputs(self):
        self.r['runs'][0]['assertions'][0]['observed']=False;reseal(self.r,'execution_root')
        with self.assertRaises(Refusal):self.check()
    def test_duplicate_scenario_cannot_replace_another(self):
        self.r['runs'][1]=copy.deepcopy(self.r['runs'][0]);reseal(self.r,'execution_root')
        with self.assertRaises(Refusal):self.check()
    def test_record_cannot_drop_assertion(self):
        self.r['runs'][0]['assertions'].pop();reseal(self.r,'execution_root')
        with self.assertRaises(Refusal):self.check()
    def test_numeric_boolean_output_refuses(self):
        self.r['runs'][0]['outputs']['a']=False;reseal(self.r,'execution_root')
        with self.assertRaises(Refusal):self.check()
    def test_record_cannot_be_promoted_to_proof(self):
        self.r['evidence_kind']='CHECKED_SOURCE_PROOF';reseal(self.r,'execution_root')
        with self.assertRaises(Refusal):self.check()
    def test_valid_actual_failure_record_is_preserved(self):
        self.s=self.s.replace('a - 2*q','a');self.r=run_feature(self.c,self.s,self.f)
        self.assertTrue(any(r['status']=='FAILED' for r in self.r['runs']));self.check()
    def test_assessment_execution_binding_is_rederived(self):
        self.s=self.s.replace('a - 2*q','a');self.r=run_feature(self.c,self.s,self.f)
        target=self.c['state_requirements']['a'];a=assess_counterexample(self.c,self.s,self.f,target)
        a['execution_root']='0'*64;reseal(a,'assessment_root')
        with self.assertRaises(Refusal):validate_assessment_record(self.c,self.s,self.f,target,self.r,a)
    def test_assessment_cannot_attribute_other_requirement(self):
        self.s=self.s.replace('a - 2*q','a');self.r=run_feature(self.c,self.s,self.f)
        target=self.c['state_requirements']['a'];a=assess_counterexample(self.c,self.s,self.f,target)
        a['failures'][0]['assertion']['requirement']=self.c['decision_requirement'];reseal(a,'assessment_root')
        with self.assertRaises(Refusal):validate_assessment_record(self.c,self.s,self.f,target,self.r,a)

class ExternalBuildReviewTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.base=Path(self.t.name)
        self.source=self.base/'source';self.source.mkdir();(self.source/'CMakeLists.txt').write_text('# explicitly synthetic\n')
        self.out=self.base/'out';self.pin=snapshot(self.source)['snapshot_root'];self.commit='e'*40
    def observe(self,callback,**kwargs):
        with patch('miw.external_build.shutil.which',return_value='/fixture/tool'),patch('miw.external_build.run_command',side_effect=callback):
            return run_zucchini(self.source,self.out,expected_source_root=self.pin,upstream_commit=self.commit,allow_trusted_build=True,**kwargs)
    def test_zero_reports_never_complete_acceptance(self):
        r=self.observe(lambda *a,**kw:{'returncode':0})
        self.assertEqual(r['status'],'BUILD_OBSERVED_NO_SUPPORTED_REPORTS');self.assertFalse(r['successful_acceptance'])
    def test_named_acceptance_report_must_exist(self):
        r=self.observe(lambda *a,**kw:{'returncode':0},accept_report_paths=['Examples/Good/BusinessRules/rules.json'])
        self.assertEqual(r['status'],'BUILD_OBSERVED_ACCEPTANCE_REPORT_MISSING')
    def test_ctest_no_tests_is_requested_as_error(self):
        calls=[]
        def cb(argv,*a,**kw):calls.append(argv);return {'returncode':0}
        self.observe(cb);self.assertIn('--no-tests=error',calls[-1])
    def test_release_configuration_reaches_build_and_ctest(self):
        calls=[]
        def cb(argv,*a,**kw):calls.append(argv);return {'returncode':0}
        self.observe(cb)
        self.assertEqual(calls[1][calls[1].index('--config')+1],'Release')
        self.assertEqual(calls[2][calls[2].index('-C')+1],'Release')
    def test_unmatched_junit_cannot_complete_acceptance(self):
        def cb(argv,*a,**kw):
            if argv[0]=='ctest':
                (self.out/'build').mkdir(exist_ok=True);(self.out/'build/report.json').write_bytes(report_bytes())
                (self.out/'ctest.xml').write_bytes(b'<testsuite><testcase name="unrelated"/></testsuite>')
            return {'returncode':0}
        r=self.observe(cb);self.assertEqual(r['status'],'BUILD_OBSERVED_NO_MATCHED_EXECUTIONS');self.assertFalse(r['successful_acceptance'])
    def test_failed_junit_cannot_be_cured_by_zero_exit_code(self):
        def cb(argv,*a,**kw):
            if argv[0]=='ctest':
                (self.out/'build').mkdir(exist_ok=True);(self.out/'build/report.json').write_bytes(report_bytes())
                (self.out/'ctest.xml').write_bytes(junit_bytes())
            return {'returncode':0}
        r=self.observe(cb);self.assertFalse(r['successful_acceptance']);self.assertGreater(r['matched_executions'],0)

class FrontendReviewTests(unittest.TestCase):
    def test_boolean_path_lowering_matches_finite_direct_execution(self):
        c,s,_=example()
        variants=[s,s.replace('a < 2*q or b < q','not (a >= 2*q and b >= q)'),
                  s.replace('a < 2*q or b < q','b < q or a < 2*q'),s.replace('q <= 0','not q > 0')]
        for source in variants:
            paths=lower_source(source,c['id'],c['parameters'],c['state'])['paths'];call=prepare_callable(c,source)
            for a in range(5):
                for b in range(4):
                    for q in range(-1,4):
                        inputs={'a':a,'b':b,'f':0,'q':q};flag,outputs=call(inputs)
                        matched=[p for p in paths if evaluate_dnf([p['guards']],inputs)]
                        self.assertTrue(matched)
                        for p in matched:
                            self.assertEqual((p['accepted'],{k:evaluate_term(v,inputs) for k,v in p['outputs'].items()}),(flag,outputs))
    def test_demorgan_source_gets_checked_proof_not_only_examples(self):
        c,s,_=example();s=s.replace('a < 2*q or b < q','not (a >= 2*q and b >= q)')
        self.assertEqual(verify_source_proof(c,s,prove_source(c,s))['outcome'],'CHECKED_SOURCE_PROOF')
    def test_no_authority_from_valid_proof(self):
        c,s,_=example();p=prove_source(c,s)
        self.assertEqual(p['standing'],'INFORMATION_ONLY');self.assertEqual(p['authority_effect'],'NONE')


class DossierReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.folder=Path(cls.temp.name)/'dossier'
        generate_demo(ROOT,cls.folder)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def tampered(self,name,mutate,field):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        d=Path(temp.name)/'copy';shutil.copytree(self.folder,d)
        record=read_json(d/name);mutate(record);reseal(record,field)
        write_json(d/name,record,replace_existing=True)
        m=read_json(d/'DEMO-MANIFEST.json')
        for row in m['files']:
            if row['path']==name:
                raw=read_bytes(d/name);row.update(sha256=digest(raw),bytes=len(raw))
        reseal(m,'manifest_root');write_json(d/'DEMO-MANIFEST.json',m,replace_existing=True)
        return d
    def test_inconsistent_execution_resealed_manifest_still_refuses(self):
        def change(r):r['runs'][0]['assertions'][0]['status']='FAILED'
        with self.assertRaisesRegex(Refusal,'EXECUTION_RECORD_INCONSISTENT'):
            verify_dossier(self.tampered('assembly.execution.json',change,'execution_root'))
    def test_unearned_live_claim_in_summary_refuses(self):
        with self.assertRaisesRegex(Refusal,'DOSSIER_UNSUPPORTED_SUMMARY_CLAIM'):
            verify_dossier(self.tampered('SUMMARY.json',lambda r:r.update(zucchini_live_cpp='PASSED'),'summary_root'))
    def test_counterexample_failure_cannot_be_removed(self):
        with self.assertRaisesRegex(Refusal,'COUNTEREXAMPLE_RECORD_INCONSISTENT'):
            verify_dossier(self.tampered('mutant.NO_A_CONSUMPTION.counterexample.json',lambda r:r.update(failures=[]),'assessment_root'))
    def test_execution_snapshot_retained_for_every_mutant(self):
        summary=read_json(self.folder/'SUMMARY.json')
        for m in summary['mutations']:self.assertTrue((self.folder/f"mutant.{m['id']}.execution.json").is_file())
        self.assertEqual(verify_dossier(self.folder)['observed_tests'],'RECORDED_NOT_RERUN')
    def test_graph_cannot_replace_observed_execution_root(self):
        def change(r):
            for n in r['nodes']:
                if n['id']=='execution':n['root']='0'*64
        with self.assertRaisesRegex(Refusal,'DOSSIER_GRAPH_BINDING_MISMATCH'):
            verify_dossier(self.tampered('graph.json',change,'graph_root'))
    def test_imported_coverage_cannot_be_relabelled_proof(self):
        def change(r):r['requirements'][0]['proof_status']='PROVED'
        with self.assertRaisesRegex(Refusal,'DOSSIER_ZUCCHINI_IMPORT_MISMATCH'):
            verify_dossier(self.tampered('zucchini.import.json',change,'import_root'))
