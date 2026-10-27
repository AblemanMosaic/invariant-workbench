import unittest
from copy import deepcopy
from itertools import product
from unittest.mock import patch
from pathlib import Path
import json
from miw.common import Refusal,digest
from miw.proofs import prove_source,verify_source_proof,derive_obligations
from miw.restricted import lower_source,evaluate_atom,evaluate_term
from miw.contracts import validate_contract
from miw.bdd import prepare_callable
from helpers import example,reseal,ROOT

class ProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,cls.s,cls.f=example();cls.p=prove_source(cls.c,cls.s)
    def test_complete_source_proof(self):
        x=verify_source_proof(self.c,self.s,self.p)
        self.assertEqual((x['outcome'],x['path_count'],x['obligation_count'],x['native_vc_count'],x['residual_count']),
                         ('CHECKED_SOURCE_PROOF',4,38,58,0))
    def test_second_domain_source_proof(self):
        c,s,_=example('allocation');p=prove_source(c,s);v=verify_source_proof(c,s,p)
        self.assertEqual((v['outcome'],v['native_vc_count']),('CHECKED_SOURCE_PROOF',28))
    def test_proof_path_never_executes_subject(self):
        with patch('builtins.exec',side_effect=AssertionError('exec forbidden in proof path')):
            p=prove_source(self.c,self.s)
        self.assertEqual(p['source_execution'],'NONE')
    def test_replay_is_deterministic(self):
        self.assertEqual(self.p,prove_source(self.c,self.s))
    def test_unchanged_ucm_modules(self):
        lock=json.loads((ROOT/'vendor/ucm/UPSTREAM-PIN.json').read_text())
        for row in lock['files']:
            self.assertEqual(digest((ROOT/row['path']).read_bytes()),row['sha256'])
    def test_actual_obligation_conservation(self):
        con=self.p['conservation']
        self.assertEqual(con['map']['status'],'PASS_CONSERVED')
        self.assertEqual(len(con['map']['edges']),38)
        self.assertTrue(all(e['disposition']=='DISCHARGED' for e in con['map']['edges']))
        self.assertTrue(all(r['checker_id']=='EXACT_NATIVE_DEDUCTIVE_PROOF_V1' for r in con['receipts']))
    def test_whitespace_source_change_invalidates(self):
        with self.assertRaises(Refusal):verify_source_proof(self.c,self.s+'\n',self.p)
    def test_contract_change_invalidates(self):
        c=deepcopy(self.c);c['title']+=' edited'
        with self.assertRaises(Refusal):verify_source_proof(c,self.s,self.p)
    def test_omit_proof_and_reseal(self):
        p=deepcopy(self.p);p['proofs'].pop();reseal(p,'proof_root')
        with self.assertRaises(Refusal):verify_source_proof(self.c,self.s,p)
    def test_omit_obligation_and_reseal(self):
        p=deepcopy(self.p);p['obligations'].pop();p['proofs'].pop();reseal(p,'proof_root')
        with self.assertRaises(Refusal):verify_source_proof(self.c,self.s,p)
    def test_reorder_proofs_and_reseal(self):
        p=deepcopy(self.p);p['proofs'][0],p['proofs'][1]=p['proofs'][1],p['proofs'][0];reseal(p,'proof_root')
        with self.assertRaises(Refusal):verify_source_proof(self.c,self.s,p)
    def test_certificate_tamper_even_resealed(self):
        p=deepcopy(self.p);bundle=p['proofs'][0]['bundle'];cert=bundle['proofs'][0]['certificate']
        cert['trace'][-1]['constraint']['bound']=999
        reseal(cert,'certificate_root');reseal(bundle,'proof_bundle_root');reseal(p,'proof_root')
        with self.assertRaises(Refusal):verify_source_proof(self.c,self.s,p)
    def test_false_authority_even_resealed(self):
        p=deepcopy(self.p);p['authority_effect']='DEPLOY';reseal(p,'proof_root')
        with self.assertRaises(Refusal):verify_source_proof(self.c,self.s,p)
    def test_trust_caveat_cannot_be_deleted(self):
        p=deepcopy(self.p);p['trust']=[];reseal(p,'proof_root')
        with self.assertRaises(Refusal):verify_source_proof(self.c,self.s,p)
    def test_false_engine_identity_refused(self):
        p=deepcopy(self.p);p['subject']['engine_root']='0'*64;reseal(p,'proof_root')
        with self.assertRaises(Refusal):verify_source_proof(self.c,self.s,p)
    def test_contradictory_precondition_refused(self):
        c=deepcopy(self.c);c['precondition']='a >= 0 and a < 0'
        with self.assertRaises(Refusal):validate_contract(c)
    def test_always_refuse_spec_without_success_witness_refused(self):
        c=deepcopy(self.c);c['accept_when']='q > 0 and q < 0'
        with self.assertRaises(Refusal):validate_contract(c)
    def test_false_nonvacuity_witness_refused(self):
        c=deepcopy(self.c);c['witnesses'][0]['accepted']=False
        with self.assertRaises(Refusal):validate_contract(c)
    def test_native_unknown_keeps_residual_obligations(self):
        s=self.s.replace('a - 2*q','a');p=prove_source(self.c,s)
        self.assertEqual(p['outcome'],'UNKNOWN_PROOF')
        self.assertGreater(len(p['conservation']['residual_inventory']['obligations']),0)
        self.assertEqual(verify_source_proof(self.c,s,p)['outcome'],'UNKNOWN_PROOF')
    def test_unknown_cannot_be_relabeled_proof(self):
        s=self.s.replace('a - 2*q','a');p=prove_source(self.c,s);p['outcome']='CHECKED_SOURCE_PROOF';reseal(p,'proof_root')
        with self.assertRaises(Refusal):verify_source_proof(self.c,s,p)
    def test_nonvacuity_catches_always_refusing_implementation(self):
        s='def assemble(a,b,f,q):\n    return (False,a,b,f)\n'
        p=prove_source(self.c,s)
        self.assertEqual(p['outcome'],'UNKNOWN_PROOF')
    def test_integer_domain_not_finite_sample_domain(self):
        call=prepare_callable(self.c,self.s);n=2**1000
        flag,out=call({'a':2*n,'b':n,'f':0,'q':n})
        self.assertTrue(flag);self.assertEqual(out,{'a':0,'b':0,'f':n})
    def test_bool_inputs_refused(self):
        call=prepare_callable(self.c,self.s)
        with self.assertRaises(Refusal):call({'a':True,'b':1,'f':0,'q':1})
    def test_float_inputs_refused(self):
        call=prepare_callable(self.c,self.s)
        with self.assertRaises(Refusal):call({'a':2.0,'b':1,'f':0,'q':1})
    def test_lowered_paths_agree_with_python_on_504_cases(self):
        call=prepare_callable(self.c,self.s);lowered=lower_source(self.s,'assemble',self.c['parameters'],self.c['state'])
        count=0
        for a,b,f,q in product(range(7),range(4),range(3),range(-1,5)):
            inputs=dict(a=a,b=b,f=f,q=q);flag,out=call(inputs)
            matching=[p for p in lowered['paths'] if all(evaluate_atom(g,inputs) for g in p['guards'])]
            self.assertTrue(matching)
            for p in matching:
                self.assertEqual(flag,p['accepted']);self.assertEqual(out,{s:evaluate_term(v,inputs) for s,v in p['outputs'].items()})
            count+=1
        self.assertEqual(count,504)

# Each case is a distinct unittest identity, not an inflated subtest count.
BAD_SOURCES={
 'import':'import os\ndef assemble(a,b,f,q):\n return (False,a,b,f)\n',
 'call':'def assemble(a,b,f,q):\n return (False,abs(a),b,f)\n',
 'attribute':'def assemble(a,b,f,q):\n return (False,a.real,b,f)\n',
 'loop':'def assemble(a,b,f,q):\n while q>0:\n  q-=1\n return (False,a,b,f)\n',
 'assignment':'def assemble(a,b,f,q):\n x=a\n return (False,x,b,f)\n',
 'default':'def assemble(a,b,f,q=1):\n return (False,a,b,f)\n',
 'decorator':'@unknown\ndef assemble(a,b,f,q):\n return (False,a,b,f)\n',
 'missing_return':'def assemble(a,b,f,q):\n if q>0:\n  return (False,a,b,f)\n',
 'nonlinear':'def assemble(a,b,f,q):\n return (True,a*q,b,f)\n',
 'floor_division':'def assemble(a,b,f,q):\n return (True,a//q,b,f)\n',
 'dynamic_status':'def assemble(a,b,f,q):\n return (q>0,a,b,f)\n',
 'chained_compare':'def assemble(a,b,f,q):\n if 0<q<a:\n  return (True,a,b,f)\n return (False,a,b,f)\n',
 'mutable_result':'def assemble(a,b,f,q):\n return [False,a,b,f]\n',
 'global_read':'def assemble(a,b,f,q):\n return (False,secret,b,f)\n',
 'unreachable_import':'def assemble(a,b,f,q):\n return (False,a,b,f)\n import os\n',
 'bool_arithmetic':'def assemble(a,b,f,q):\n return (False,True+b,b,f)\n',
}
for name,source in BAD_SOURCES.items():
    def case(self,source=source):
        c,_,_=example()
        with self.assertRaises(Refusal):derive_obligations(c,source)
    setattr(ProofTests,'test_refuse_unsupported_'+name,case)
