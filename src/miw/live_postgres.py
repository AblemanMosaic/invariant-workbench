"""Opt-in disposable PostgreSQL acceptance campaign, never run implicitly.

Creates a new tenant in the fixed reference schema. It does not wipe an existing
schema or tenant. Use a dedicated, nonproduction database. Test rows remain for
inspection. The DSN is not written to evidence. This is integration testing.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import threading
import uuid
from .common import Refusal, require, seal, write_json, BOUNDARY
from .lifecycle import command, validate_state
from .postgres import PostgresRepository, connect_factory, initialize_local_reference, OutcomeUnknown

def run_live(out:Path,*,allow_disposable_database:bool=False,dsn:str|None=None)->dict:
    require(allow_disposable_database is True,'DISPOSABLE_DATABASE_EXECUTION_NOT_ADMITTED')
    require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS')
    dsn=dsn if dsn is not None else os.environ.get('MIW_TEST_PG_DSN')
    if not dsn:
        out.mkdir(parents=True)
        result=seal({'schema':'miw.postgres_live_campaign.v1',**BOUNDARY,'status':'NOT_RUN',
                     'reason':'MIW_TEST_PG_DSN_NOT_SUPPLIED','passed_cases':0,'live_postgres':False})
        write_json(out/'SUMMARY.json',result);return result
    connect=connect_factory(dsn)
    tenant='miw_'+uuid.uuid4().hex
    out.mkdir(parents=True)
    observed=[];initialized=False
    def record(name,condition):
        require(condition,'LIVE_POSTGRES_ASSERTION',detail=name);observed.append({'id':name,'status':'PASSED'})
    try:
        initialize_local_reference(connect,tenant,a=2,b=1,allow_setup=True);initialized=True
        repo=PostgresRepository(connect,allow_experimental_effects=True)
        def cmd(action,payload,op):return command(action,payload,op,tenant)
        barrier=threading.Barrier(2)
        competing=[cmd('RESERVE',{'order_id':o,'recipe_id':'r1','quantity':1},'reserve_'+o) for o in ('one','two')]
        def apply(c):barrier.wait(timeout=10);return repo.apply(c)
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(apply,competing))
        record('two_orders_last_kit',sorted(r['outcome']['status'] for r in results)==['ACCEPTED','REFUSED'])
        winner=next(r for r in results if r['outcome']['status']=='ACCEPTED');oid=winner['request']['payload']['order_id']
        with ThreadPoolExecutor(max_workers=2) as pool:replays=list(pool.map(repo.apply,[winner['request']]*2))
        record('concurrent_duplicate_returns_exact_original',replays==[winner,winner])
        altered=dict(winner['request']);altered['payload']=dict(altered['payload'],quantity=2)
        try:repo.apply(altered);mismatch=False
        except Refusal as exc:mismatch=exc.code=='OPERATION_ID_REUSED_WITH_DIFFERENT_REQUEST'
        record('operation_id_payload_reuse_refused',mismatch)
        premature=repo.apply(cmd('COMPLETE',{'order_id':oid},'premature'))
        record('completion_requires_consumption',premature['outcome']['status']=='REFUSED')
        # Real SQL transaction plus deliberately raised pre-COMMIT host exception.
        class InterruptBeforeCommit:
            def __init__(self,c):self.c=c
            def execute(self,sql,params=None):
                result=self.c.execute(sql,params) if params is not None else self.c.execute(sql)
                if sql.startswith('UPDATE miw_reference'):raise RuntimeError('TEST_INTERRUPTION_BEFORE_COMMIT')
                return result
            def __getattr__(self,k):return getattr(self.c,k)
        interrupted=cmd('RECEIVE',{'a':1,'b':0},'rollback_probe')
        try:PostgresRepository(lambda:InterruptBeforeCommit(connect()),allow_experimental_effects=True).apply(interrupted);aborted=False
        except Refusal as exc:aborted=exc.code=='DATABASE_TRANSACTION_ABORTED'
        record('interrupted_transaction_aborted',aborted)
        record('rollback_has_no_receipt',repo.reconcile(interrupted).get('status')=='NOT_OBSERVED')
        consumed=repo.apply(cmd('CONSUME',{'order_id':oid},'consume'))
        record('consumption_attributed',consumed['outcome']['status']=='ACCEPTED')
        # Simulate only the lost acknowledgement AFTER a real DB COMMIT.
        class DropCommitAcknowledgement:
            def __init__(self,c):self.c=c
            def commit(self):self.c.commit();raise ConnectionError('TEST_ACK_LOSS_AFTER_REAL_COMMIT')
            def __getattr__(self,k):return getattr(self.c,k)
        completion=cmd('COMPLETE',{'order_id':oid},'complete')
        try:PostgresRepository(lambda:DropCommitAcknowledgement(connect()),allow_experimental_effects=True).apply(completion);unknown=False
        except OutcomeUnknown:unknown=True
        record('lost_ack_remains_unknown',unknown)
        resolved=repo.reconcile(completion)
        record('lost_ack_reconciled_from_receipt',resolved['outcome']['status']=='ACCEPTED')
        record('resolved_replay_no_duplicate',repo.apply(completion)==resolved)
        with connect() as c:
            version=c.execute('SHOW server_version').fetchone()[0]
            state=validate_state(c.execute('SELECT state FROM miw_reference.tenants WHERE tenant=%s',(tenant,)).fetchone()[0])
            count=c.execute('SELECT count(*) FROM miw_reference.receipts WHERE tenant=%s',(tenant,)).fetchone()[0]
        record('completed_with_empty_shelves',state['finished']==1 and state['available_a']==state['available_b']==0)
        result=seal({'schema':'miw.postgres_live_campaign.v1',**BOUNDARY,'status':'PASSED_LIVE_INTEGRATION_TESTS',
                     'live_postgres':True,'tenant':tenant,'server_version':version,'cases':observed,
                     'passed_cases':len(observed),'final_state':state,'receipt_count':count,
                     'faults':'HOST_INJECTION_AROUND_REAL_SQL_NOT_PHYSICAL_NETWORK_CHAOS',
                     'formal_concurrency_proof':False,'production_authority':False,
                     'writer_boundary':'TRUSTED_REFERENCE_ROLE; OTHER_WRITERS_AND_ADMINISTRATORS_NOT_CONTROLLED',
                     'cleanup':'NEW_TENANT_RETAINED_FOR_INSPECTION'})
    except Exception as exc:
        result=seal({'schema':'miw.postgres_live_campaign.v1',**BOUNDARY,'status':'FAILED_LIVE_CAMPAIGN',
                     'live_postgres':initialized,'tenant':tenant,'cases':observed,'passed_cases':len(observed),
                     'error_type':type(exc).__name__,'error_code':getattr(exc,'code','HOST_OR_DATABASE_ERROR'),
                     'cleanup':'NO_DESTRUCTIVE_CLEANUP; INSPECT_NEW_TENANT_IF_CREATED'})
    write_json(out/'SUMMARY.json',result);return result
