"""Bounded, pure work-order reference model. Tested, not formally verified as a whole.

Available inventory is distinct from reserved and attributed consumption. Recipes
are immutable by revision. Completing consumed work does not require shelf stock.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
from typing import Any
from .common import Refusal, require, exact_keys, root, seal, BOUNDARY, identifier, digest, read_bytes, check_seal

MAX_VALUE = 2**63 - 1
MAX_ORDERS = 128
MAX_RECIPES = 16
ACTIONS = {'RECEIVE', 'ADD_RECIPE', 'RESERVE', 'CONSUME', 'COMPLETE', 'CANCEL'}
STATUSES = {'RESERVED', 'CONSUMED', 'COMPLETED', 'CANCELLED'}
STATE_KEYS = {'schema','revision','available_a','available_b','reserved_a','reserved_b',
              'received_a','received_b','finished','recipes','orders'}

def integer(x: Any, label: str, minimum: int=0) -> int:
    require(type(x) is int and minimum <= x <= MAX_VALUE, 'INTEGER_RANGE', detail=label)
    return x

def recipe(a: int, b: int) -> dict:
    integer(a,'recipe.a',1); integer(b,'recipe.b',1)
    return {'a': a, 'b': b}

def initial_state(a: int=0, b: int=0) -> dict:
    integer(a,'a'); integer(b,'b')
    return {'schema':'miw.work_order_state.v1','revision':0,'available_a':a,'available_b':b,
            'reserved_a':0,'reserved_b':0,'received_a':a,'received_b':b,'finished':0,
            'recipes':{'r1':recipe(2,1)},'orders':{}}

def validate_state(state: dict) -> dict:
    exact_keys(state,STATE_KEYS)
    require(state['schema']=='miw.work_order_state.v1','STATE_SCHEMA')
    for k in STATE_KEYS-{'schema','recipes','orders'}: integer(state[k],k)
    require(type(state['recipes']) is dict and 0 < len(state['recipes']) <= MAX_RECIPES,'RECIPE_LIMIT')
    for name,r in state['recipes'].items():
        identifier(name);exact_keys(r,{'a','b'});recipe(r['a'],r['b'])
    require(type(state['orders']) is dict and len(state['orders']) <= MAX_ORDERS,'ORDER_LIMIT')
    reserved_a=reserved_b=consumed_a=consumed_b=finished=0
    for name,o in state['orders'].items():
        identifier(name);exact_keys(o,{'recipe_id','recipe_root','quantity','status','consumed_a','consumed_b'})
        identifier(o['recipe_id']);require(o['recipe_id'] in state['recipes'],'ORDER_RECIPE_MISSING')
        r=state['recipes'][o['recipe_id']]
        require(o['recipe_root']==root(r),'ORDER_RECIPE_CHANGED')
        integer(o['quantity'],'quantity',1);integer(o['consumed_a'],'consumed_a');integer(o['consumed_b'],'consumed_b')
        require(type(o['status']) is str and o['status'] in STATUSES,'ORDER_STATUS')
        need_a=r['a']*o['quantity'];need_b=r['b']*o['quantity']
        integer(need_a,'need_a');integer(need_b,'need_b')
        if o['status'] in {'CONSUMED','COMPLETED'}:
            require((o['consumed_a'],o['consumed_b'])==(need_a,need_b),'CONSUMPTION_ATTRIBUTION_INVALID')
            consumed_a+=need_a;consumed_b+=need_b
        else:require(o['consumed_a']==o['consumed_b']==0,'UNISSUED_CONSUMPTION')
        if o['status']=='RESERVED':reserved_a+=need_a;reserved_b+=need_b
        if o['status']=='COMPLETED':finished+=o['quantity']
    require((reserved_a,reserved_b)==(state['reserved_a'],state['reserved_b']),'RESERVATION_ACCOUNTING')
    require(state['finished']==finished,'OUTPUT_ACCOUNTING')
    require(state['available_a']+reserved_a+consumed_a==state['received_a'],'A_CONSERVATION')
    require(state['available_b']+reserved_b+consumed_b==state['received_b'],'B_CONSERVATION')
    return state

def _payload(action: str,p: dict) -> None:
    require(type(action) is str and action in ACTIONS,'ACTION_UNSUPPORTED')
    fields={'RECEIVE':{'a','b'},'ADD_RECIPE':{'recipe_id','a','b'},
            'RESERVE':{'order_id','recipe_id','quantity'},
            'CONSUME':{'order_id'},'COMPLETE':{'order_id'},'CANCEL':{'order_id'}}
    exact_keys(p,fields[action])
    for key in ('order_id','recipe_id'):
        if key in p:identifier(p[key])
    for key in ('a','b','quantity'):
        if key in p:integer(p[key],key,1 if action=='ADD_RECIPE' or key=='quantity' else 0)

def transition(state: dict,action: str,payload: dict) -> tuple[dict,dict]:
    """No I/O. Structural invalidity raises; business refusal leaves state exact."""
    validate_state(state);_payload(action,payload)
    s=deepcopy(state);p=payload
    def refuse(reason):return deepcopy(state),{'status':'REFUSED','reason':reason}
    if action=='RECEIVE':
        if not (p['a'] or p['b']):return refuse('EMPTY_RECEIPT')
        if s['received_a']+p['a']>MAX_VALUE or s['received_b']+p['b']>MAX_VALUE:return refuse('INTEGER_CAPACITY')
        for x in ('a','b'):s['available_'+x]+=p[x];s['received_'+x]+=p[x]
    elif action=='ADD_RECIPE':
        if p['recipe_id'] in s['recipes']:return refuse('RECIPE_VERSION_EXISTS')
        if len(s['recipes'])>=MAX_RECIPES:return refuse('RECIPE_CAPACITY')
        s['recipes'][p['recipe_id']]=recipe(p['a'],p['b'])
    elif action=='RESERVE':
        if p['order_id'] in s['orders']:return refuse('ORDER_EXISTS')
        if len(s['orders'])>=MAX_ORDERS:return refuse('ORDER_CAPACITY')
        if p['recipe_id'] not in s['recipes']:return refuse('RECIPE_UNKNOWN')
        r=s['recipes'][p['recipe_id']];a=r['a']*p['quantity'];b=r['b']*p['quantity']
        if max(a,b)>MAX_VALUE:return refuse('INTEGER_CAPACITY')
        if a>s['available_a'] or b>s['available_b']:return refuse('INSUFFICIENT_COMPONENTS')
        s['available_a']-=a;s['available_b']-=b;s['reserved_a']+=a;s['reserved_b']+=b
        s['orders'][p['order_id']]={'recipe_id':p['recipe_id'],'recipe_root':root(r),'quantity':p['quantity'],
                                  'status':'RESERVED','consumed_a':0,'consumed_b':0}
    else:
        if p['order_id'] not in s['orders']:return refuse('ORDER_UNKNOWN')
        o=s['orders'][p['order_id']];r=s['recipes'][o['recipe_id']];a=r['a']*o['quantity'];b=r['b']*o['quantity']
        if action=='CONSUME':
            if o['status']!='RESERVED':return refuse('ORDER_NOT_RESERVED')
            s['reserved_a']-=a;s['reserved_b']-=b;o.update(status='CONSUMED',consumed_a=a,consumed_b=b)
        elif action=='COMPLETE':
            if o['status']!='CONSUMED':return refuse('CONSUMPTION_REQUIRED')
            if s['finished']+o['quantity']>MAX_VALUE:return refuse('INTEGER_CAPACITY')
            s['finished']+=o['quantity'];o['status']='COMPLETED'
        elif action=='CANCEL':
            if o['status']!='RESERVED':return refuse('CANCELLATION_REQUIRES_UNCONSUMED_RESERVATION')
            s['reserved_a']-=a;s['reserved_b']-=b;s['available_a']+=a;s['available_b']+=b;o['status']='CANCELLED'
    if s['revision']==MAX_VALUE:return refuse('REVISION_CAPACITY')
    s['revision']+=1;validate_state(s)
    return s,{'status':'ACCEPTED','reason':action+'_RECORDED'}

def validate_command(c: dict) -> dict:
    exact_keys(c,{'schema','tenant','operation_id','action','payload'})
    require(c['schema']=='miw.inventory_command.v1','COMMAND_SCHEMA')
    identifier(c['tenant']);identifier(c['operation_id']);_payload(c['action'],c['payload'])
    return c

def command(action: str,payload: dict,operation_id: str,tenant: str='demo') -> dict:
    return validate_command({'schema':'miw.inventory_command.v1','tenant':tenant,'operation_id':operation_id,'action':action,'payload':payload})

def receipt(c: dict,before: dict,after: dict,outcome: dict) -> dict:
    return seal({'schema':'miw.inventory_receipt.v1',**BOUNDARY,'request':deepcopy(c),'request_root':root(c),
                 'before_root':root(before),'after_root':root(after),'outcome':outcome,
                 'state_revision':after['revision'],'model_source_file_sha256_observed':digest(read_bytes(Path(__file__))), 'evidence_class':'REFERENCE_MODEL_EXECUTION_NOT_PROOF'})

def validate_receipt(value: dict, c: dict) -> dict:
    """Check stored record structure and binding, not provenance or execution truth."""
    validate_command(c)
    check_seal(value)
    exact_keys(value, {'schema','standing','authority_effect','request','request_root',
                      'before_root','after_root','outcome','state_revision',
                      'model_source_file_sha256_observed','evidence_class','record_root'})
    require(value['schema'] == 'miw.inventory_receipt.v1' and
            all(value[k] == v for k,v in BOUNDARY.items()), 'DATABASE_RECEIPT_BOUNDARY')
    validate_command(value['request'])
    require(value['request'] == c and root(value['request']) == root(c) and value['request_root'] == root(c), 'DATABASE_RECEIPT_BINDING')
    require(value['evidence_class'] == 'REFERENCE_MODEL_EXECUTION_NOT_PROOF', 'DATABASE_RECEIPT_EVIDENCE_CLASS')
    for field in ('before_root','after_root','model_source_file_sha256_observed'):
        item=value[field]
        require(type(item) is str and len(item)==64 and all(ch in '0123456789abcdef' for ch in item),
                'DATABASE_RECEIPT_DIGEST')
    integer(value['state_revision'], 'receipt.revision')
    outcome=exact_keys(value['outcome'], {'status','reason'})
    require(outcome['status'] in ('ACCEPTED','REFUSED') and type(outcome['status']) is str,
            'DATABASE_RECEIPT_OUTCOME')
    require(type(outcome['reason']) is str and bool(outcome['reason']), 'DATABASE_RECEIPT_REASON')
    if outcome['status']=='REFUSED':
        require(value['before_root']==value['after_root'], 'DATABASE_REFUSAL_MUTATES_STATE')
    else:
        require(outcome['reason']==c['action']+'_RECORDED' and value['state_revision']>0 and
                value['before_root']!=value['after_root'], 'DATABASE_ACCEPTED_TRANSITION_INVALID')
    return deepcopy(value)

class MemoryRepository:
    """Deterministic sequential reference, explicitly not a database substitute."""
    def __init__(self,tenant: str='demo',state: dict|None=None):
        self.tenant=identifier(tenant);self.state=deepcopy(validate_state(initial_state() if state is None else state));self.receipts={}
    def apply(self,c: dict) -> dict:
        validate_command(c);require(c['tenant']==self.tenant,'TENANT_MISMATCH')
        key=c['operation_id']
        if key in self.receipts:
            r=self.receipts[key];require(r['request_root']==root(c),'OPERATION_ID_REUSED_WITH_DIFFERENT_REQUEST')
            return deepcopy(r)
        after,outcome=transition(self.state,c['action'],c['payload']);r=receipt(c,self.state,after,outcome)
        self.state=after;self.receipts[key]=r;return deepcopy(r)
    def reconcile(self,c: dict) -> dict:
        validate_command(c);require(c['tenant']==self.tenant,'TENANT_MISMATCH')
        r=self.receipts.get(c['operation_id'])
        if r is not None:
            require(r['request_root']==root(c),'OPERATION_ID_REUSED_WITH_DIFFERENT_REQUEST');return deepcopy(r)
        return {'status':'NOT_OBSERVED','not_executed_claim':False,**BOUNDARY}

def lifecycle_demo() -> dict:
    repo=MemoryRepository(state=initial_state(2,1));records=[]
    plan=[('RESERVE',{'order_id':'first','recipe_id':'r1','quantity':1}),
          ('RESERVE',{'order_id':'competing','recipe_id':'r1','quantity':1}),
          ('COMPLETE',{'order_id':'first'}),('CONSUME',{'order_id':'first'}),
          ('ADD_RECIPE',{'recipe_id':'r2','a':3,'b':1}),('COMPLETE',{'order_id':'first'})]
    for i,(a,p) in enumerate(plan):records.append(repo.apply(command(a,p,'op_'+str(i))))
    replay=repo.apply(records[-1]['request'])
    return seal({'schema':'miw.lifecycle_demo.v1',**BOUNDARY,'receipts':records,'state':repo.state,
                 'duplicate_returns_original':replay==records[-1],'completion_with_empty_shelves':repo.state['finished']==1 and repo.state['available_a']==repo.state['available_b']==0,
                 'claim':'TESTED_REFERENCE_LIFECYCLE_NOT_FORMAL_SYSTEM_PROOF',
                 'residual':['arbitrary maps and concurrency outside native arithmetic proof','physical inventory truth','database correspondence and all-writer boundary']})

def bounded_exploration() -> dict:
    """Exhaust the declared finite alphabet, not all possible workflows."""
    start=initial_state(4,2);start['recipes']['r2']=recipe(3,1)
    alphabet=[]
    for oid in ('one','two'):
        for rid in ('r1','r2'):alphabet.append(('RESERVE',{'order_id':oid,'recipe_id':rid,'quantity':1}))
        for action in ('CONSUME','COMPLETE','CANCEL'):alphabet.append((action,{'order_id':oid}))
    states={root(start):start};pending=[start];edges=accepted=refused=0
    while pending:
        state=pending.pop()
        for action,payload in alphabet:
            after,out=transition(state,action,payload);edges+=1
            # Independent observations, rather than trusting a stored PASS label.
            require(all(after[k]>=0 for k in ('available_a','available_b','reserved_a','reserved_b','finished')),'EXPLORE_NEGATIVE')
            if out['status']=='REFUSED':
                require(after==state,'EXPLORE_REFUSAL_MUTATED');refused+=1
            else:accepted+=1
            for o in after['orders'].values():
                if o['status']=='COMPLETED':
                    r=after['recipes'][o['recipe_id']]
                    require(o['consumed_a']==r['a']*o['quantity'] and o['consumed_b']==r['b']*o['quantity'],'EXPLORE_UNBACKED_COMPLETION')
            key=root(after)
            if key not in states:
                require(len(states)<5000,'EXPLORATION_STATE_LIMIT');states[key]=after;pending.append(after)
    return seal({'schema':'miw.bounded_lifecycle_exploration.v1',**BOUNDARY,
                 'status':'CHECKED_FINITE_REFERENCE_GRAPH','states':len(states),'edges':edges,
                 'accepted_edges':accepted,'refused_edges':refused,'frontier_remaining':len(pending),
                 'initial_state':start,'alphabet':[[a,p] for a,p in alphabet],
                 'all_state_roots':sorted(states),'unbounded_proof':False,'live_database_execution':False,
                 'excluded':['receiving new stock','unbounded orders or quantities','administrator writes','concurrency','crashes','physical truth']})
