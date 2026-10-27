"""Optional model proposals. Untrusted text never edits an approved basis.

The local Ollama transport is explicit opt-in and proposal-only. The review path
is usable offline with any model's response, including manually prepared files.
"""
from __future__ import annotations
from copy import deepcopy
import json
import urllib.request
import urllib.error
from .common import Refusal,require,exact_keys,seal,check_seal,root,digest,strict_loads,BOUNDARY,canonical_bytes
from .contracts import validate_contract
from .bdd import discover,assess_counterexample

MAX_RESPONSE=512*1024

def proposal_request(contract:dict,source:str,target:str,basis_root:str,*,budget:int=3)->dict:
    validate_contract(contract)
    require(type(source) is str and len(source.encode())<MAX_RESPONSE,'PROPOSAL_SOURCE_LIMIT')
    require(type(target) is str and target,'PROPOSAL_TARGET_REQUIRED')
    require(type(basis_root) is str and len(basis_root)==64 and all(c in '0123456789abcdef' for c in basis_root),'PROPOSAL_BASIS_ROOT')
    require(type(budget) is int and 1<=budget<=16,'PROPOSAL_BUDGET')
    # The named target is validated against the approved requirement IDs, not the model.
    from .contracts import requirement_ids
    require(target in requirement_ids(contract),'PROPOSAL_TARGET_UNKNOWN')
    return seal({'schema':'miw.proposal_request.v1',**BOUNDARY,'contract':deepcopy(contract),
                 'source':source,'source_sha256':digest(source.encode()),'contract_root':root(contract),
                 'target':target,'basis_root':basis_root,'maximum_scenarios':budget,
                 'permitted_output':'SCENARIO_PROPOSAL_ONLY',
                 'scenario_vocabulary':['Feature: <name>','Scenario: <name>', 'Given inputs '+', '.join(n+'=<integer>' for n in contract['parameters']), 'When '+contract['id']+' is requested','Then acceptance is true OR Then acceptance is false','And <state parameter> is <integer>'],
                 'response_shape':{'kind':'SCENARIO_PROPOSAL','request_root':'Copy the outer request_root exactly','feature':'A complete native scalar feature as a string'},
                 'instruction':'Propose a failing scenario using the existing native scalar vocabulary. Do not change requirements, source, runner, or checks. Return JSON with kind, request_root, feature. No failure found is not proof.'},'request_root')

def validate_proposal_request(request: dict) -> dict:
    check_seal(request, 'request_root')
    fields = {'schema','standing','authority_effect','contract','source','source_sha256',
              'contract_root','target','basis_root','maximum_scenarios','permitted_output',
              'scenario_vocabulary','response_shape','instruction','request_root'}
    exact_keys(request, fields)
    expected = proposal_request(request['contract'], request['source'], request['target'],
                                request['basis_root'], budget=request['maximum_scenarios'])
    require(canonical_bytes(request) == canonical_bytes(expected), 'PROPOSAL_REQUEST_SEMANTICS_MISMATCH')
    return request

def review_proposal(request:dict,response:bytes,*,expected_request_root:str,current_contract:dict,
                    current_source:str,current_basis_root:str)->dict:
    validate_proposal_request(request)
    require(request['request_root']==expected_request_root,'PROPOSAL_REQUEST_PIN_MISMATCH')
    require(request['contract_root']==root(current_contract) and request['source_sha256']==digest(current_source.encode())
            and request['basis_root']==current_basis_root,'STALE_PROPOSAL_CONTEXT')
    require(type(response) is bytes and len(response)<=MAX_RESPONSE,'PROPOSAL_RESPONSE_LIMIT')
    proposal=strict_loads(response);exact_keys(proposal,{'kind','request_root','feature'})
    require(proposal['kind']=='SCENARIO_PROPOSAL','PROPOSAL_KIND_NOT_PERMITTED')
    require(proposal['request_root']==expected_request_root,'PROPOSAL_RESPONSE_PIN_MISMATCH')
    require(type(proposal['feature']) is str,'PROPOSAL_FEATURE_REQUIRED')
    discovered=discover(current_contract,proposal['feature'])
    require(len(discovered['scenarios'])<=request['maximum_scenarios'],'PROPOSAL_SCENARIO_BUDGET')
    assessed=assess_counterexample(current_contract,current_source,proposal['feature'],request['target'])
    return seal({'schema':'miw.proposal_review.v1',**BOUNDARY,'request_root':expected_request_root,
                 'response_sha256':digest(response),'discovery':discovered,'assessment':assessed,
                 'specification_approval':'NOT_GRANTED','canonical_source_changed':False,
                 'model_assertions_accepted_as_evidence':False,'approval_required_for_new_specification':True})

def ollama_propose(request:dict,model:str,*,allow_local_model:bool=False,port:int=11434,timeout:float=60)->bytes:
    require(allow_local_model is True,'LOCAL_MODEL_NOT_ENABLED');validate_proposal_request(request)
    require(type(model) is str and 0<len(model)<=200,'MODEL_ID_REQUIRED')
    require(type(port) is int and 1<=port<=65535,'LOCAL_MODEL_PORT')
    require(type(timeout) in (int,float) and 0<timeout<=120,'LOCAL_MODEL_TIMEOUT')
    prompt=json.dumps(request,sort_keys=True)
    data=json.dumps({'model':model,'stream':False,'format':'json','messages':[
        {'role':'system','content':request['instruction']},
        {'role':'user','content':prompt}]}).encode()
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):raise Refusal('MODEL_REDIRECT_REFUSED')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    req=urllib.request.Request(f'http://127.0.0.1:{port}/api/chat',data=data,headers={'Content-Type':'application/json'})
    try:
        with opener.open(req,timeout=timeout) as stream:raw=stream.read(MAX_RESPONSE+1)
    except (OSError,urllib.error.URLError) as exc:raise Refusal('LOCAL_MODEL_UNAVAILABLE',detail=type(exc).__name__) from exc
    require(len(raw)<=MAX_RESPONSE,'PROPOSAL_RESPONSE_LIMIT')
    outer=strict_loads(raw)
    require(type(outer) is dict and outer.get('done') is True,'MODEL_RESPONSE_INCOMPLETE')
    require(type(outer) is dict and type(outer.get('message')) is dict and type(outer['message'].get('content')) is str,'MODEL_RESPONSE_SHAPE')
    return outer['message']['content'].encode()
