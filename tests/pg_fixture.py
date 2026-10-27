"""Deterministic SQL protocol fixture. NOT PostgreSQL and NOT concurrency evidence."""
from copy import deepcopy
import json
from types import SimpleNamespace
from miw.postgres import LOCK_SQL,READ_SQL,UPDATE_SQL,INSERT_SQL
class DatabaseError(Exception):
    def __init__(self,state=None):self.sqlstate=state
class Row:
    def __init__(self,row):self.row=row
    def fetchone(self):return self.row
class Database:
    def __init__(self,state):self.state=deepcopy(state);self.receipts={};self.calls=[];self.opened=0;self.failures=[]
    def connect(self):self.opened+=1;return Connection(self)
class Connection:
    def __init__(self,db):self.db=db;self.state=deepcopy(db.state);self.receipts=deepcopy(db.receipts);self.closed=False;self.autocommit=False;self.info=SimpleNamespace(transaction_status=0)
    def execute(self,sql,args=None):
        self.db.calls.append((sql,args))
        if self.db.failures and self.db.failures[0][0]==sql:
            _,state=self.db.failures.pop(0);raise DatabaseError(state)
        if sql==LOCK_SQL:return Row((deepcopy(self.state),))
        if sql==READ_SQL:return Row(self.receipts.get((args[0],args[1])))
        if sql==UPDATE_SQL:self.state=json.loads(args[0]);return Row(None)
        if sql==INSERT_SQL:
            self.receipts[(args[0],args[1])]=(args[2],json.loads(args[3]));return Row(None)
        if sql.startswith('SET TRANSACTION'):return Row(None)
        raise AssertionError('Unexpected SQL '+sql)
    def commit(self):
        if self.db.failures and self.db.failures[0][0]=='COMMIT_ABORT':
            _,state=self.db.failures.pop(0);raise DatabaseError(state)
        self.db.state=deepcopy(self.state);self.db.receipts=deepcopy(self.receipts)
        if self.db.failures and self.db.failures[0][0]=='COMMIT_LOST':
            self.db.failures.pop(0);raise DatabaseError()
    def rollback(self):self.db.calls.append(('ROLLBACK',None))
    def close(self):self.closed=True;self.db.calls.append(('CLOSE',None))
