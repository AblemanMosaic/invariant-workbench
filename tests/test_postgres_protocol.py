import unittest
from copy import deepcopy
from miw.postgres import *
from miw.lifecycle import command,initial_state
from pg_fixture import Database

class PostgresProtocolFixtureTests(unittest.TestCase):
    def setUp(self):
        self.db=Database(initial_state(2,1));self.repo=PostgresRepository(self.db.connect,allow_experimental_effects=True,sleep=lambda _:None)
        self.c=command('RESERVE',{'order_id':'one','recipe_id':'r1','quantity':1},'reserve')
    def test_effects_require_explicit_opt_in(self):
        with self.assertRaises(Refusal):PostgresRepository(self.db.connect)
    def test_serializable_before_reads(self):
        self.repo.apply(self.c);self.assertEqual(self.db.calls[0][0],'SET TRANSACTION ISOLATION LEVEL SERIALIZABLE');self.assertEqual(self.db.calls[1][0],LOCK_SQL)
    def test_state_and_receipt_commit_together(self):
        r=self.repo.apply(self.c);self.assertEqual(self.db.state['available_a'],0);self.assertEqual(self.db.receipts[('demo','reserve')][1],r)
    def test_same_request_replays_without_update(self):
        r=self.repo.apply(self.c);self.db.calls=[];self.assertEqual(self.repo.apply(self.c),r);self.assertNotIn(UPDATE_SQL,[c[0] for c in self.db.calls])
    def test_id_reuse_with_changed_request_refuses(self):
        self.repo.apply(self.c);c=deepcopy(self.c);c['payload']['quantity']=2
        with self.assertRaises(Refusal):self.repo.apply(c)
    def test_serialization_retry_repeats_entire_transaction(self):
        self.db.failures=[(UPDATE_SQL,'40001')];r=self.repo.apply(self.c)
        self.assertEqual(r['outcome']['status'],'ACCEPTED');self.assertEqual(self.db.opened,2);self.assertEqual(sum(s==LOCK_SQL for s,_ in self.db.calls),2)
    def test_deadlock_retry(self):
        self.db.failures=[(LOCK_SQL,'40P01')];self.repo.apply(self.c);self.assertEqual(self.db.opened,2)
    def test_retry_exhaustion_refuses(self):
        self.db.failures=[(LOCK_SQL,'40001')]*4
        with self.assertRaisesRegex(Refusal,'TRANSACTION_RETRY_EXHAUSTED'):self.repo.apply(self.c)
        self.assertEqual(self.db.state,initial_state(2,1))
    def test_exception_before_commit_rolls_back(self):
        self.db.failures=[(INSERT_SQL,'XX000')]
        with self.assertRaisesRegex(Refusal,'DATABASE_TRANSACTION_ABORTED'):self.repo.apply(self.c)
        self.assertEqual(self.db.state,initial_state(2,1));self.assertEqual(self.db.receipts,{})
    def test_lost_commit_response_is_unknown(self):
        self.db.failures=[('COMMIT_LOST',None)]
        with self.assertRaises(OutcomeUnknown):self.repo.apply(self.c)
        self.assertEqual(self.db.opened,1);self.assertEqual(self.repo.reconcile(self.c)['outcome']['status'],'ACCEPTED')
    def test_resubmit_after_lost_commit_has_no_second_effect(self):
        self.db.failures=[('COMMIT_LOST',None)]
        with self.assertRaises(OutcomeUnknown):self.repo.apply(self.c)
        r=self.repo.apply(self.c);self.assertEqual(r['state_revision'],1);self.assertEqual(self.db.state['revision'],1)
    def test_commit_serialization_abort_is_retryable(self):
        self.db.failures=[('COMMIT_ABORT','40001')];self.repo.apply(self.c);self.assertEqual(self.db.state['revision'],1);self.assertEqual(self.db.opened,2)
    def test_absent_receipt_does_not_prove_nonexecution(self):self.assertFalse(self.repo.reconcile(self.c)['not_executed_claim'])
    def test_reconcile_checks_exact_request(self):
        self.repo.apply(self.c);c=deepcopy(self.c);c['payload']['quantity']=2
        with self.assertRaises(Refusal):self.repo.reconcile(c)
    def test_corrupt_receipt_detected(self):
        self.repo.apply(self.c);self.db.receipts[('demo','reserve')][1]['state_revision']=999
        with self.assertRaises(Refusal):self.repo.reconcile(self.c)
    def test_corrupt_database_state_detected(self):
        self.db.state['finished']=99
        with self.assertRaises(Refusal):self.repo.apply(self.c)
    def test_structural_input_rejected_before_connect(self):
        c=deepcopy(self.c);c['payload']['quantity']=True
        with self.assertRaises(Refusal):self.repo.apply(c)
        self.assertEqual(self.db.opened,0)
    def test_refusal_gets_durable_idempotent_record(self):
        c=command('COMPLETE',{'order_id':'missing'},'missing');r=self.repo.apply(c)
        self.assertEqual(r['outcome']['status'],'REFUSED');self.assertEqual(r,self.repo.apply(c));self.assertEqual(self.db.state['revision'],0)
