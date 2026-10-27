import unittest,json
from copy import deepcopy
from unittest.mock import patch
from helpers import example
from miw.proposals import *
from miw.changes import explain_change
from miw.common import Refusal,root
from miw.contracts import requirement_ids

class ProposalTests(unittest.TestCase):
    def setUp(self):
        self.c,self.s,self.f=example();self.target=self.c['decision_requirement'];self.basis='a'*64
        self.req=proposal_request(self.c,self.s,self.target,self.basis,budget=8)
    def response(self,**kw):
        x={'kind':'SCENARIO_PROPOSAL','request_root':self.req['request_root'],'feature':self.f};x.update(kw);return json.dumps(x).encode()
    def review(self,response=None,**kw):
        args={'expected_request_root':self.req['request_root'],'current_contract':self.c,'current_source':self.s,'current_basis_root':self.basis};args.update(kw)
        return review_proposal(self.req,response or self.response(),**args)
    def test_proposal_is_not_specification_approval(self):
        r=self.review();self.assertEqual(r['specification_approval'],'NOT_GRANTED');self.assertFalse(r['canonical_source_changed'])
    def test_no_failure_does_not_become_proof(self):
        r=self.review();self.assertFalse(r['assessment']['proof_claim']);self.assertEqual(r['assessment']['outcome'],'NO_TARGET_COUNTEREXAMPLE_FOUND')
    def test_stale_source_refused(self):
        with self.assertRaises(Refusal):self.review(current_source=self.s+'\n')
    def test_stale_basis_refused(self):
        with self.assertRaises(Refusal):self.review(current_basis_root='b'*64)
    def test_stale_contract_refused(self):
        c=deepcopy(self.c);c['title']='new'
        with self.assertRaises(Refusal):self.review(current_contract=c)
    def test_wrong_request_root_refused(self):
        with self.assertRaises(Refusal):self.review(self.response(request_root='0'*64))
    def test_extra_instruction_not_admitted(self):
        with self.assertRaises(Refusal):self.review(self.response(changes=[{'path':'contract.json','text':'weaken'}]))
    def test_model_cannot_approve_itself(self):
        with self.assertRaises(Refusal):self.review(self.response(kind='APPROVED_PROOF'))
    def test_nonjson_model_text_refused(self):
        with self.assertRaises(Refusal):self.review(b'I certify everything correct')
    def test_unknown_requirement_refused(self):
        with self.assertRaises(Refusal):proposal_request(self.c,self.s,'UNKNOWN',self.basis)
    def test_model_call_disabled_by_default(self):
        with patch('urllib.request.build_opener') as op:
            with self.assertRaises(Refusal):ollama_propose(self.req,'model')
            op.assert_not_called()
    def test_scenario_budget_enforced(self):
        self.req=proposal_request(self.c,self.s,self.target,self.basis,budget=1)
        with self.assertRaises(Refusal):self.review()
    def test_unrelated_failure_is_not_target_counterexample(self):
        self.s=self.s.replace('a - 2*q','a');self.req=proposal_request(self.c,self.s,self.target,self.basis,budget=8)
        r=self.review();self.assertEqual(r['assessment']['outcome'],'NO_TARGET_COUNTEREXAMPLE_FOUND')
    def test_relevant_failure_retained(self):
        self.s=self.s.replace('a - 2*q','a');self.target=self.c['state_requirements']['a'];self.req=proposal_request(self.c,self.s,self.target,self.basis,budget=8)
        self.assertEqual(self.review()['assessment']['outcome'],'REPRODUCED_REQUIREMENT_FAILURE')
    def test_modified_request_seal_refuses(self):
        self.req['maximum_scenarios']=16
        with self.assertRaises(Refusal):self.review()

class ChangeExplanationTests(unittest.TestCase):
    def setUp(self):self.c,self.s,_=example()
    def test_identical_inputs(self):
        r=explain_change(self.c,self.c,self.s,self.s);self.assertEqual(r['required_action'],'NO_CHANGED_INPUTS')
    def test_comment_change_still_requalifies(self):
        r=explain_change(self.c,self.c,self.s,self.s+'\n# comment\n');self.assertEqual(r['required_action'],'FULL_REQUALIFICATION');self.assertEqual(r['semantic_equivalence'],'NOT_ESTABLISHED')
    def test_contract_metadata_requires_review(self):
        c=deepcopy(self.c);c['title']='Different title';r=explain_change(self.c,c,self.s,self.s);self.assertEqual(r['approval'],'HUMAN_REQUIRED_FOR_CONTRACT_CHANGE')
    def test_precondition_change_explicitly_flagged(self):
        c=deepcopy(self.c);c['precondition']+=' and q >= 0'
        r=explain_change(self.c,c,self.s,self.s);self.assertEqual(r['contract_changes'][0]['classification'],'PRECONDITION_CHANGED_POSSIBLE_DOMAIN_NARROWING')

class LocalModelTransportTests(unittest.TestCase):
    def setUp(self):
        c,s,_=example();self.req=proposal_request(c,s,c['decision_requirement'],'a'*64)
    def response(self,body):
        from unittest.mock import MagicMock
        stream=MagicMock();stream.__enter__.return_value=stream;stream.read.return_value=json.dumps(body).encode()
        return stream
    def test_completed_loopback_reply_is_still_only_text(self):
        from unittest.mock import MagicMock
        opener=MagicMock();opener.open.return_value=self.response({'done':True,'message':{'content':'{"kind":"SCENARIO_PROPOSAL"}'}})
        with patch('urllib.request.build_opener',return_value=opener):raw=ollama_propose(self.req,'local-test',allow_local_model=True)
        request=opener.open.call_args.args[0]
        self.assertEqual(request.full_url,'http://127.0.0.1:11434/api/chat')
        self.assertFalse(json.loads(request.data)['stream']);self.assertIsInstance(raw,bytes)
    def test_partial_model_reply_refused(self):
        from unittest.mock import MagicMock
        opener=MagicMock();opener.open.return_value=self.response({'done':False,'message':{'content':'{}'}})
        with patch('urllib.request.build_opener',return_value=opener):
            with self.assertRaises(Refusal):ollama_propose(self.req,'local-test',allow_local_model=True)
    def test_missing_content_refused(self):
        from unittest.mock import MagicMock
        opener=MagicMock();opener.open.return_value=self.response({'done':True})
        with patch('urllib.request.build_opener',return_value=opener):
            with self.assertRaises(Refusal):ollama_propose(self.req,'local-test',allow_local_model=True)
    def test_invalid_port_refused_before_request(self):
        with patch('urllib.request.build_opener') as opener:
            with self.assertRaises(Refusal):ollama_propose(self.req,'x',allow_local_model=True,port=65536)
            opener.assert_not_called()
    def test_transport_failure_is_not_success(self):
        from unittest.mock import MagicMock
        opener=MagicMock();opener.open.side_effect=OSError('fixture unavailable')
        with patch('urllib.request.build_opener',return_value=opener):
            with self.assertRaises(Refusal):ollama_propose(self.req,'x',allow_local_model=True)
    def test_request_includes_machine_vocabulary(self):
        self.assertTrue(any('Given inputs' in x for x in self.req['scenario_vocabulary']))
