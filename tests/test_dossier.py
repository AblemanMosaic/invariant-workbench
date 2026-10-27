import unittest,tempfile,shutil,json
from pathlib import Path
from copy import deepcopy
from miw.common import Refusal,write_json,read_json,seal,digest
from miw.dossier import generate_demo,verify_dossier,render_summary
from miw.proofs import prove_source,verify_source_proof
from helpers import ROOT,example,reseal

class DossierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.folder=Path(cls.temp.name)/'demo'
        cls.summary=generate_demo(ROOT,cls.folder)
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def test_complete_dossier_replays(self):
        c=verify_dossier(self.folder)
        self.assertEqual(len(c['native_proof_checks']),2);self.assertEqual(len(c['mutant_proof_checks']),7)
        self.assertEqual(c['observed_tests'],'RECORDED_NOT_RERUN')
    def test_proof_before_execution_phase_order(self):
        for name in ('assembly','allocation'):
            phases=[p['phase'] for p in self.summary['phases'] if p['example']==name]
            self.assertEqual(phases,['STATIC_PROOF_BUILT','STATIC_PROOF_RECHECKED','EXAMPLES_EXECUTED'])
    def test_seven_mutants_have_both_negative_evidence_types(self):
        self.assertEqual(len(self.summary['mutations']),7)
        for m in self.summary['mutations']:
            self.assertEqual(m['proof_outcome'],'UNKNOWN_PROOF')
            self.assertGreater(m['residual_count'],0)
            self.assertEqual(m['counterexample_outcome'],'REPRODUCED_REQUIREMENT_FAILURE')
    def test_offline_html_escapes_untrusted_labels(self):
        s=deepcopy(self.summary);s['examples'][0]['name']='<script>alert(1)</script>'
        html=render_summary(s)
        self.assertNotIn('<script>',html);self.assertIn('&lt;script&gt;',html)
    def test_summary_cannot_inflate_proof_after_resealing(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/'copy';shutil.copytree(self.folder,d)
            s=read_json(d/'SUMMARY.json');s['examples'][0]['native_vc_count']=99999;reseal(s,'summary_root');write_json(d/'SUMMARY.json',s,replace_existing=True)
            m=read_json(d/'DEMO-MANIFEST.json')
            for row in m['files']:
                if row['path']=='SUMMARY.json':
                    data=(d/'SUMMARY.json').read_bytes();row['sha256']=digest(data);row['bytes']=len(data)
            reseal(m,'manifest_root');write_json(d/'DEMO-MANIFEST.json',m,replace_existing=True)
            with self.assertRaises(Refusal):verify_dossier(d)
    def test_extra_dossier_file_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/'copy';shutil.copytree(self.folder,d);(d/'extra.txt').write_text('unlisted')
            with self.assertRaises(Refusal):verify_dossier(d)
    def test_old_output_directory_not_overwritten(self):
        with self.assertRaises(Refusal):generate_demo(ROOT,self.folder)

    def test_governance_fixture_uses_exact_lf_source_bytes(self):
        source=(ROOT/'examples/assembly/operation.py').read_bytes().decode('utf-8').encode('utf-8')
        governance=read_json(self.folder/'governance.demo.json')
        row=next(item for item in governance['basis']['snapshot']['files'] if item['path']=='operation.py')
        self.assertEqual(row['bytes'],len(source));self.assertEqual(row['sha256'],digest(source))

    def test_manifest_uses_platform_independent_name_order(self):
        paths=[row['path'] for row in read_json(self.folder/'DEMO-MANIFEST.json')['files']]
        self.assertEqual(paths,sorted(paths))

    def test_graph_separates_scenario_specification_from_observed_execution(self):
        nodes={n['id']:n for n in read_json(self.folder/'graph.json')['nodes']}
        self.assertEqual(nodes['scenarios']['kind'],'SCENARIO_SPECIFICATION')
        self.assertEqual(nodes['execution']['kind'],'EXECUTED_EXAMPLES')
        self.assertEqual(nodes['execution']['root'],read_json(self.folder/'assembly.execution.json')['execution_root'])
        self.assertEqual(nodes['scenarios']['root'],digest((self.folder/'assembly.feature').read_bytes()))
    def test_different_feature_cannot_reuse_old_recorded_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/'copy';shutil.copytree(self.folder,d)
            f=d/'assembly.feature';f.write_text(f.read_text()+'\n# Changed exact feature snapshot\n')
            m=read_json(d/'DEMO-MANIFEST.json')
            for row in m['files']:
                if row['path']=='assembly.feature':
                    data=f.read_bytes();row['sha256']=digest(data);row['bytes']=len(data)
            reseal(m,'manifest_root');write_json(d/'DEMO-MANIFEST.json',m,replace_existing=True)
            with self.assertRaises(Refusal):verify_dossier(d)
    def test_counterexample_cannot_change_feature_identity_after_resealing(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp)/'copy';shutil.copytree(self.folder,d)
            name='mutant.NO_A_CONSUMPTION.counterexample.json'
            c=read_json(d/name);c['feature_sha256']='0'*64;reseal(c,'assessment_root');write_json(d/name,c,replace_existing=True)
            m=read_json(d/'DEMO-MANIFEST.json')
            for row in m['files']:
                if row['path']==name:
                    data=(d/name).read_bytes();row['sha256']=digest(data);row['bytes']=len(data)
            reseal(m,'manifest_root');write_json(d/'DEMO-MANIFEST.json',m,replace_existing=True)
            with self.assertRaises(Refusal):verify_dossier(d)

class AdditionalProofTests(unittest.TestCase):
    def test_semantically_equivalent_refactoring_still_proves(self):
        c,s,_=example();s=s.replace('a < 2*q or b < q','b < q or a < 2*q')
        p=prove_source(c,s);self.assertEqual(verify_source_proof(c,s,p)['outcome'],'CHECKED_SOURCE_PROOF')
    def test_scope_inflation_even_resealed_is_refused(self):
        c,s,_=example();p=prove_source(c,s);p['proof_scope']='All C++ and physical warehouses';reseal(p,'proof_root')
        with self.assertRaises(Refusal):verify_source_proof(c,s,p)
