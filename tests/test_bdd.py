import unittest
from miw.common import Refusal
from miw.bdd import discover,run_feature,assess_counterexample,parse_feature
from helpers import example

class BDDTests(unittest.TestCase):
    def setUp(self):self.c,self.s,self.f=example()
    def test_examples_all_execute(self):
        r=run_feature(self.c,self.s,self.f)
        self.assertEqual(len(r['runs']),5);self.assertTrue(all(x['status']=='PASSED' for x in r['runs']))
        self.assertEqual(r['evidence_kind'],'EXECUTED_EXAMPLES')
    def test_discovery_does_not_claim_execution(self):
        d=discover(self.c,self.f);self.assertEqual(d['implementation_execution'],'NONE')
    def test_unasserted_invariants_remain_uncovered(self):
        d=discover(self.c,self.f);self.assertIn('REQ_A_CONSERVATION',d['uncovered'])
    def test_explicit_invariant_assertion_counts(self):
        f=self.f+'  And invariant REQ_A_CONSERVATION holds\n'
        d=discover(self.c,f);self.assertNotIn('REQ_A_CONSERVATION',d['uncovered'])
    def test_contradictory_expectation_rejects_scenario(self):
        f=self.f.replace('And a is 0','And a is 1',1);r=run_feature(self.c,self.s,f)
        self.assertEqual(r['runs'][0]['status'],'DISCOVERY_REJECTED')
        self.assertEqual(r['runs'][0]['assertions'],[])
    def test_exact_failure_attribution(self):
        s=self.s.replace('a - 2*q','a')
        r=assess_counterexample(self.c,s,self.f,'REQ_A_ACCOUNTING')
        self.assertEqual(r['outcome'],'REPRODUCED_REQUIREMENT_FAILURE');self.assertEqual(len(r['failures']),2)
    def test_other_assertion_failure_not_target_counterexample(self):
        s=self.s.replace('a - 2*q','a')
        r=assess_counterexample(self.c,s,self.f,'REQ_B_ACCOUNTING')
        self.assertEqual(r['outcome'],'NO_TARGET_COUNTEREXAMPLE_FOUND');self.assertFalse(r['proof_claim'])
    def test_absent_vocabulary_check_not_no_counterexample(self):
        r=assess_counterexample(self.c,self.s,self.f,'REQ_A_CONSERVATION')
        self.assertEqual(r['outcome'],'TARGET_NOT_EXERCISED')
    def test_unknown_target_refused(self):
        with self.assertRaises(Refusal):assess_counterexample(self.c,self.s,self.f,'NOT_A_REQUIREMENT')
    def test_second_domain(self):
        c,s,f=example('allocation');r=run_feature(c,s,f)
        self.assertTrue(all(x['status']=='PASSED' for x in r['runs']))

BAD_FEATURES={
 'outline':'Feature: X\nScenario Outline: X\n',
 'background':'Feature: X\nBackground:\n',
 'no_assertion':'Feature: X\nScenario: X\nGiven inputs a=2,b=1,f=0,q=1\nWhen assemble is requested\n',
 'wrong_when':'Feature: X\nScenario: X\nGiven inputs a=2,b=1,f=0,q=1\nWhen allocate is requested\nThen acceptance is true\n',
 'unknown_input':'Feature: X\nScenario: X\nGiven inputs a=2,b=1,f=0,x=1\nWhen assemble is requested\nThen acceptance is true\n',
 'duplicate_input':'Feature: X\nScenario: X\nGiven inputs a=2,a=3,b=1,f=0,q=1\n',
 'and_before_then':'Feature: X\nScenario: X\nGiven inputs a=2,b=1,f=0,q=1\nWhen assemble is requested\nAnd a is 0\n',
 'no_feature':'Scenario: X\n',
 'duplicate_feature':'Feature: X\nFeature: Y\n',
 'negative_initial_state':'Feature: X\nScenario: X\nGiven inputs a=-1,b=1,f=0,q=1\nWhen assemble is requested\nThen acceptance is true\n',
}
for name,text in BAD_FEATURES.items():
    def case(self,text=text):
        with self.assertRaises(Refusal):parse_feature(text,self.c)
    setattr(BDDTests,'test_refuse_'+name,case)
