"""Explicit, optional psycopg3 PostgreSQL reference adapter.

One tenant row is locked per command. Receipt and state are committed together.
This deliberately coarse lock favors an inspectable reference over throughput.
Unit-driver tests are not evidence of live PostgreSQL transaction behavior.
"""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Callable,Any
from .common import Refusal,require,root,check_seal,canonical_bytes,BOUNDARY,identifier
from .lifecycle import initial_state,validate_state,validate_command,transition,receipt,validate_receipt

LOCK_SQL='SELECT state FROM miw_reference.tenants WHERE tenant = %s FOR UPDATE'
READ_SQL='SELECT request_root, receipt FROM miw_reference.receipts WHERE tenant = %s AND operation_id = %s'
UPDATE_SQL='UPDATE miw_reference.tenants SET state = %s::jsonb WHERE tenant = %s'
INSERT_SQL='INSERT INTO miw_reference.receipts (tenant, operation_id, request_root, receipt) VALUES (%s, %s, %s, %s::jsonb)'

class OutcomeUnknown(Refusal):
    def __init__(self,c:dict):
        self.request_root=root(c);self.operation_id=c['operation_id']
        super().__init__('EFFECT_OUTCOME_UNKNOWN_RECONCILE_SAME_OPERATION',detail=self.operation_id)

def _decoded(x:Any)->dict:
    if type(x) is str:
        from .common import strict_loads
        return strict_loads(x)
    require(type(x) is dict,'DATABASE_JSON_INVALID');return x

def _stored(row,c):
    require(type(row) in (tuple,list) and len(row)==2,'DATABASE_RECEIPT_SHAPE')
    require(row[0]==root(c),'OPERATION_ID_REUSED_WITH_DIFFERENT_REQUEST')
    return validate_receipt(_decoded(row[1]), c)

def _transaction_connection(conn):
    # The public injectable factory is required to return a fresh idle connection,
    # not merely one on which SET TRANSACTION happens to return successfully.
    require(getattr(conn, 'autocommit', None) is False, 'DATABASE_EXPLICIT_TRANSACTION_REQUIRED')
    status = getattr(getattr(conn, 'info', None), 'transaction_status', None)
    require(isinstance(status, int) and not isinstance(status, bool) and int(status) == 0,
            'DATABASE_IDLE_CONNECTION_REQUIRED')
    return conn

class PostgresRepository:
    def __init__(self,connect:Callable[[],Any],*,allow_experimental_effects:bool=False,
                 max_attempts:int=4,sleep:Callable[[float],None]=time.sleep):
        require(allow_experimental_effects is True,'DATABASE_EFFECTS_NOT_ENABLED')
        require(type(max_attempts) is int and 1<=max_attempts<=8,'DATABASE_RETRY_BOUND')
        self.connect=connect;self.max_attempts=max_attempts;self.sleep=sleep
    def apply(self,c:dict)->dict:
        validate_command(c)
        for attempt in range(self.max_attempts):
            conn=None;commit_attempted=False
            try:
                conn=self.connect();_transaction_connection(conn)
                # First transaction statement, before any data reads.
                conn.execute('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE')
                row=conn.execute(LOCK_SQL,(c['tenant'],)).fetchone()
                require(row is not None,'TENANT_UNKNOWN')
                state=validate_state(_decoded(row[0]))
                old=conn.execute(READ_SQL,(c['tenant'],c['operation_id'])).fetchone()
                if old is not None:
                    result=_stored(old,c);conn.rollback();return result
                after,outcome=transition(state,c['action'],c['payload'])
                result=receipt(c,state,after,outcome)
                conn.execute(UPDATE_SQL,(canonical_bytes(after).decode(),c['tenant']))
                conn.execute(INSERT_SQL,(c['tenant'],c['operation_id'],root(c),canonical_bytes(result).decode()))
                commit_attempted=True;conn.commit();return result
            except Refusal as exc:
                if conn is not None:
                    try:conn.rollback()
                    except Exception:pass
                if commit_attempted:raise OutcomeUnknown(c) from exc
                raise
            except Exception as exc:
                if conn is not None:
                    try:conn.rollback()
                    except Exception:pass
                # PostgreSQL explicitly aborted these transactions, including a
                # serialization failure reported by COMMIT. Whole transaction retry.
                if getattr(exc,'sqlstate',None) in {'40001','40P01'}:
                    if attempt+1==self.max_attempts:raise Refusal('TRANSACTION_RETRY_EXHAUSTED') from exc
                    self.sleep(min(0.01*2**attempt,0.2));continue
                if commit_attempted:raise OutcomeUnknown(c) from exc
                raise Refusal('DATABASE_TRANSACTION_ABORTED',detail=type(exc).__name__) from exc
            finally:
                if conn is not None:
                    try:conn.close()
                    except Exception:pass
        raise Refusal('TRANSACTION_RETRY_EXHAUSTED')
    def reconcile(self,c:dict)->dict:
        validate_command(c);conn=None
        try:
            conn=self.connect();_transaction_connection(conn);conn.execute('SET TRANSACTION READ ONLY')
            row=conn.execute(READ_SQL,(c['tenant'],c['operation_id'])).fetchone()
            if row is None:
                return {'status':'NOT_OBSERVED','not_executed_claim':False,**BOUNDARY,
                        'request_root':root(c),'next_action':'RECONCILE_OR_RESUBMIT_EXACT_IDEMPOTENT_REQUEST'}
            return _stored(row,c)
        finally:
            if conn is not None:
                try:conn.rollback()
                finally:conn.close()

def connect_factory(dsn:str)->Callable:
    """No connection until called. DSN is neither recorded nor sent to AI."""
    require(type(dsn) is str and bool(dsn),'DATABASE_DSN_REQUIRED')
    try:import psycopg
    except ImportError as exc:raise Refusal('PSYCOPG3_NOT_INSTALLED') from exc
    return lambda:psycopg.connect(dsn,autocommit=False,connect_timeout=5)

def initialize_local_reference(connect:Callable,tenant:str,*,a:int=0,b:int=0,allow_setup:bool=False)->None:
    require(allow_setup is True,'DATABASE_SETUP_NOT_ENABLED');identifier(tenant)
    state=initial_state(a,b);conn=connect()
    try:
        _transaction_connection(conn)
        sql=(Path(__file__).resolve().parents[2]/'sql/reference.sql').read_text()
        conn.execute(sql)
        conn.execute('INSERT INTO miw_reference.tenants (tenant,state) VALUES (%s,%s::jsonb)',
                     (tenant,canonical_bytes(state).decode()))
        conn.commit()
    except Exception:
        conn.rollback();raise
    finally:conn.close()
