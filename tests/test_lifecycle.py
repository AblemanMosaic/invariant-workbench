import unittest
from copy import deepcopy
from miw.lifecycle import *
from miw.common import Refusal

class LifecycleTests(unittest.TestCase):
    def setUp(self):self.repo=MemoryRepository(state=initial_state(4,2));self.index=0
    def act(self,a,p):
        self.index+=1;return self.repo.apply(command(a,p,'n'+str(self.index)))
    def reserve(self,oid='one',rid='r1',q=1):return self.act('RESERVE',{'order_id':oid,'recipe_id':rid,'quantity':q})
    def test_complete_without_consumption_refuses(self):
        self.reserve();before=deepcopy(self.repo.state);r=self.act('COMPLETE',{'order_id':'one'})
        self.assertEqual(r['outcome']['reason'],'CONSUMPTION_REQUIRED');self.assertEqual(before,self.repo.state)
    def test_empty_shelves_after_consumption_can_complete(self):
        self.reserve(q=2);self.act('CONSUME',{'order_id':'one'});r=self.act('COMPLETE',{'order_id':'one'})
        self.assertEqual(r['outcome']['status'],'ACCEPTED');self.assertEqual(self.repo.state['finished'],2);self.assertEqual(self.repo.state['available_a'],0)
    def test_last_stock_not_double_reserved(self):
        self.reserve(q=2);r=self.reserve('two');self.assertEqual(r['outcome']['reason'],'INSUFFICIENT_COMPONENTS')
    def test_consumption_cannot_be_reused(self):
        self.reserve();self.act('CONSUME',{'order_id':'one'});self.act('COMPLETE',{'order_id':'one'})
        self.assertEqual(self.act('COMPLETE',{'order_id':'one'})['outcome']['status'],'REFUSED');self.assertEqual(self.repo.state['finished'],1)
    def test_reservation_cancellation_returns_stock(self):
        self.reserve(q=2);self.act('CANCEL',{'order_id':'one'});self.assertEqual(self.repo.state['available_a'],4);self.assertEqual(self.repo.state['reserved_a'],0)
    def test_cancellation_after_consumption_refuses(self):
        self.reserve();self.act('CONSUME',{'order_id':'one'});self.assertEqual(self.act('CANCEL',{'order_id':'one'})['outcome']['status'],'REFUSED')
    def test_recipe_revision_is_immutable(self):
        before=deepcopy(self.repo.state);r=self.act('ADD_RECIPE',{'recipe_id':'r1','a':3,'b':1});self.assertEqual(r['outcome']['status'],'REFUSED');self.assertEqual(before,self.repo.state)
    def test_new_recipe_does_not_change_existing_order(self):
        self.reserve();self.act('ADD_RECIPE',{'recipe_id':'r2','a':3,'b':1});self.act('CONSUME',{'order_id':'one'})
        self.assertEqual(self.repo.state['orders']['one']['consumed_a'],2)
    def test_missing_recipe_refuses(self):self.assertEqual(self.reserve(rid='unknown')['outcome']['reason'],'RECIPE_UNKNOWN')
    def test_missing_order_refuses(self):self.assertEqual(self.act('CONSUME',{'order_id':'unknown'})['outcome']['reason'],'ORDER_UNKNOWN')
    def test_cancelled_order_identity_not_reused(self):
        self.reserve();self.act('CANCEL',{'order_id':'one'});self.assertEqual(self.reserve()['outcome']['reason'],'ORDER_EXISTS')
    def test_same_operation_returns_exact_receipt(self):
        c=command('RECEIVE',{'a':2,'b':1},'one');r=self.repo.apply(c);self.assertEqual(r,self.repo.apply(c));self.assertEqual(self.repo.state['available_a'],6)
    def test_changed_operation_payload_refused(self):
        c=command('RECEIVE',{'a':2,'b':1},'one');self.repo.apply(c);c['payload']['a']=3
        with self.assertRaises(Refusal):self.repo.apply(c)
    def test_unobserved_is_not_nonexecution(self):self.assertFalse(self.repo.reconcile(command('RECEIVE',{'a':1,'b':0},'new'))['not_executed_claim'])
    def test_refusal_remains_refusal_on_retry_after_receiving(self):
        c=command('RESERVE',{'order_id':'one','recipe_id':'r1','quantity':4},'same');r=self.repo.apply(c);self.act('RECEIVE',{'a':10,'b':10});self.assertEqual(self.repo.apply(c),r)
    def test_tenant_mismatch(self):
        with self.assertRaises(Refusal):self.repo.apply(command('RECEIVE',{'a':1,'b':0},'new','other'))
    def test_bool_is_not_inventory_integer(self):
        with self.assertRaises(Refusal):initial_state(True,1)
    def test_negative_inventory_refused(self):
        with self.assertRaises(Refusal):initial_state(-1,1)
    def test_quantity_zero_invalid(self):
        with self.assertRaises(Refusal):self.reserve(q=0)
    def test_quantity_overflow_refuses_without_state_change(self):
        self.assertEqual(self.reserve(q=MAX_VALUE)['outcome']['reason'],'INTEGER_CAPACITY')
    def test_receive_overflow_refuses(self):
        self.repo=MemoryRepository(state=initial_state(MAX_VALUE,0));r=self.act('RECEIVE',{'a':1,'b':0});self.assertEqual(r['outcome']['reason'],'INTEGER_CAPACITY')
    def test_unsupported_fields_refused(self):
        with self.assertRaises(Refusal):self.act('RECEIVE',{'a':1,'b':0,'override':True})
    def test_unbacked_finished_state_detected(self):
        s=initial_state();s['finished']=1
        with self.assertRaises(Refusal):validate_state(s)
    def test_corrupt_reservation_detected(self):
        s=initial_state();s['reserved_a']=1
        with self.assertRaises(Refusal):validate_state(s)
    def test_corrupt_recipe_binding_detected(self):
        self.reserve();s=deepcopy(self.repo.state);s['recipes']['r1']['a']=3
        with self.assertRaises(Refusal):validate_state(s)
    def test_bounded_exploration_exhausts_declared_graph(self):
        r=bounded_exploration();self.assertEqual(r['frontier_remaining'],0);self.assertGreater(r['states'],20);self.assertFalse(r['unbounded_proof'])
    def test_demo_separates_business_refusals(self):
        r=lifecycle_demo();self.assertTrue(r['duplicate_returns_original']);self.assertTrue(r['completion_with_empty_shelves'])
