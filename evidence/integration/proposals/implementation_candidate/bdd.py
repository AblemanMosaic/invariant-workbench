"""Native, deliberately small BDD profile. Not a full Gherkin implementation."""
from __future__ import annotations
import re
from copy import deepcopy
from .common import BOUNDARY, Refusal, require, root, seal, digest, check_seal, exact_keys, canonical_bytes
from .contracts import validate_contract, validate_inputs, expected_result, requirement_ids
from .restricted import lower_source, parse_dnf, evaluate_dnf

MAX_SCENARIOS=128

def _assertion(c:dict,text:str,line:int) -> dict:
    if text in ('acceptance is true','acceptance is false'):
        return {'kind':'DECISION','target':'accepted','expected':text.endswith('true'),
                'requirement':c['decision_requirement'],'line':line}
    match=re.fullmatch(r'([A-Za-z_][A-Za-z0-9_]*) is (-?\d{1,19})',text)
    if match:
        name,value=match.groups();require(name in c['state'],'ASSERTION_STATE_UNKNOWN')
        return {'kind':'STATE','target':name,'expected':int(value),'requirement':c['state_requirements'][name],'line':line}
    match=re.fullmatch(r'invariant ([A-Za-z_][A-Za-z0-9_]*) holds',text)
    if match:
        rid=match.group(1);require(rid in {i['id'] for i in c['invariants']},'ASSERTION_INVARIANT_UNKNOWN')
        return {'kind':'INVARIANT','target':rid,'expected':True,'requirement':rid,'line':line}
    raise Refusal('BDD_ASSERTION_UNSUPPORTED',detail=f'line {line}')

def parse_feature(text:str,contract:dict) -> dict:
    c=validate_contract(contract)
    require(type(text) is str and len(text.encode('utf-8'))<=128_000,'FEATURE_SIZE_LIMIT')
    feature=None;scenarios=[];current=None;phase='START'
    def finish():
        if current is not None:
            require(phase=='ASSERT' and current['assertions'],'SCENARIO_INCOMPLETE',detail=current['name'])
    for number,raw in enumerate(text.splitlines(),1):
        line=raw.strip()
        if not line or line.startswith('#'):continue
        if line.startswith('Feature: '):
            require(feature is None and current is None,'FEATURE_DUPLICATE')
            feature=line[9:].strip();require(bool(feature),'FEATURE_NAME_REQUIRED');phase='FEATURE'
        elif line.startswith('Scenario: '):
            require(feature is not None,'FEATURE_REQUIRED');finish()
            name=line[10:].strip();require(bool(name) and name not in {s['name'] for s in scenarios},'SCENARIO_NAME_INVALID')
            require(len(scenarios)<MAX_SCENARIOS,'SCENARIO_LIMIT')
            current={'id':f's{len(scenarios):03d}','name':name,'line':number,'inputs':{},'assertions':[]}
            scenarios.append(current);phase='SCENARIO'
        elif line.startswith('Given inputs '):
            require(current is not None and phase=='SCENARIO','GIVEN_ORDER_INVALID')
            for item in line[len('Given inputs '):].split(','):
                m=re.fullmatch(r'\s*([A-Za-z_][A-Za-z0-9_]*)=(-?\d{1,19})\s*',item)
                require(m is not None,'BDD_INPUT_INVALID',detail=f'line {number}')
                key,value=m.groups();require(key not in current['inputs'],'BDD_DUPLICATE_INPUT')
                current['inputs'][key]=int(value)
            validate_inputs(c,current['inputs']);phase='GIVEN'
        elif line.startswith('When '):
            require(phase=='GIVEN' and line==f'When {c["id"]} is requested','WHEN_INVALID')
            phase='WHEN'
        elif line.startswith(('Then ','And ')):
            keyword,body=line.split(' ',1)
            require((keyword=='Then' and phase=='WHEN') or (keyword=='And' and phase=='ASSERT'),'ASSERTION_ORDER_INVALID')
            assertion=_assertion(c,body,number)
            require(not any(a['kind']==assertion['kind'] and a['target']==assertion['target'] for a in current['assertions']),
                    'DUPLICATE_ASSERTION')
            current['assertions'].append(assertion);phase='ASSERT'
        else:
            raise Refusal('BDD_SYNTAX_UNSUPPORTED',detail=f'line {number}: {line[:80]}')
    finish();require(feature is not None and scenarios,'FEATURE_HAS_NO_SCENARIOS')
    return {'feature':feature,'scenarios':scenarios}

def assertion_value(c:dict,a:dict,inputs:dict,flag:bool,outputs:dict):
    if a['kind']=='DECISION': return flag
    if a['kind']=='STATE': return outputs[a['target']]
    inv=next(x for x in c['invariants'] if x['id']==a['target'])
    env={**inputs,**{'out_'+k:v for k,v in outputs.items()}}
    return evaluate_dnf(parse_dnf(inv['formula'],set(env)),env)

def discover(contract:dict,text:str) -> dict:
    c=validate_contract(contract);parsed=parse_feature(text,c)
    for scenario in parsed['scenarios']:
        flag,outputs=expected_result(c,scenario['inputs'])
        violations=[];coverage=[]
        for assertion in scenario['assertions']:
            expected=assertion_value(c,assertion,scenario['inputs'],flag,outputs)
            if type(expected) is not type(assertion['expected']) or expected!=assertion['expected']:
                violations.append({'requirement':assertion['requirement'],'line':assertion['line'],
                                   'expected_by_contract':expected,'declared':assertion['expected']})
            else:
                coverage.append({'requirement':assertion['requirement'],'line':assertion['line']})
        scenario['accepted']=not violations;scenario['violations']=violations
        scenario['coverage']=coverage
    covered={x['requirement'] for s in parsed['scenarios'] if s['accepted'] for x in s['coverage']}
    return seal({'schema':'miw.native_discovery.v1',**BOUNDARY,'profile':'MIW_BDD_SCALAR_V1',
        'contract_root':root(c),'feature_sha256':digest(text.encode('utf-8')),**parsed,
        'requirements':requirement_ids(c),'uncovered':sorted(set(requirement_ids(c))-covered),
        'discovery_success':all(s['accepted'] for s in parsed['scenarios']),
        'implementation_execution':'NONE','claim':'Scenario expectations checked against this contract, not a proof of implementation'},'discovery_root')

def prepare_callable(contract:dict,source:str):
    """Execute only an AST accepted by the closed pure-operation subset."""
    c=validate_contract(contract)
    lower_source(source,c['id'],c['parameters'],c['state'])
    environment={'__builtins__':{}}
    exec(compile(source,'<miw-checked-subset>','exec'),environment,environment)
    function=environment[c['id']]
    def call(values:dict):
        validate_inputs(c,values)
        result=function(*(values[p] for p in c['parameters']))
        require(type(result) is tuple and len(result)==len(c['state'])+1,'EXECUTION_RETURN_INVALID')
        require(type(result[0]) is bool and all(type(x) is int for x in result[1:]),'EXECUTION_RETURN_TYPE_INVALID')
        return result[0],dict(zip(c['state'],result[1:],strict=True))
    return call

def run_feature(contract:dict,source:str,text:str) -> dict:
    c=validate_contract(contract);d=discover(c,text);call=prepare_callable(c,source)
    runs=[]
    for scenario in d['scenarios']:
        if not scenario['accepted']:
            runs.append({'scenario_id':scenario['id'],'status':'DISCOVERY_REJECTED','assertions':[]})
            continue
        flag,outputs=call(scenario['inputs']);assertions=[]
        for a in scenario['assertions']:
            observed=assertion_value(c,a,scenario['inputs'],flag,outputs)
            passed=type(observed) is type(a['expected']) and observed==a['expected']
            assertions.append({**a,'observed':observed,'status':'PASSED' if passed else 'FAILED'})
        runs.append({'scenario_id':scenario['id'],'status':'PASSED' if all(a['status']=='PASSED' for a in assertions) else 'FAILED',
                     'accepted':flag,'outputs':outputs,'assertions':assertions})
    return seal({'schema':'miw.native_execution.v1',**BOUNDARY,'source_sha256':digest(source.encode('utf-8')),
        'contract_root':root(c),'discovery_root':d['discovery_root'],'discovery':d,'runs':runs,
        'evidence_kind':'EXECUTED_EXAMPLES','claim':'Only the recorded executions, not a universal proof'},'execution_root')

def validate_execution_record(contract:dict,source:str,text:str,record:dict) -> dict:
    """Recheck record consistency without executing the source or attesting origin."""
    c=validate_contract(contract);lower_source(source,c['id'],c['parameters'],c['state'])
    d=discover(c,text);check_seal(record,'execution_root')
    exact_keys(record,{'schema','standing','authority_effect','source_sha256','contract_root',
        'discovery_root','discovery','runs','evidence_kind','claim','execution_root'})
    require(record['schema']=='miw.native_execution.v1' and all(record[k]==v for k,v in BOUNDARY.items()),
            'EXECUTION_RECORD_BOUNDARY')
    require(record['source_sha256']==digest(source.encode('utf-8')) and record['contract_root']==root(c),
            'EXECUTION_RECORD_SUBJECT')
    require(record['discovery_root']==d['discovery_root'] and canonical_bytes(record['discovery'])==canonical_bytes(d),
            'EXECUTION_RECORD_DISCOVERY')
    require(record['evidence_kind']=='EXECUTED_EXAMPLES' and record['claim']=='Only the recorded executions, not a universal proof',
            'EXECUTION_RECORD_CLAIM')
    require(type(record['runs']) is list and len(record['runs'])==len(d['scenarios']), 'EXECUTION_RECORD_COVERAGE')
    for scenario,run in zip(d['scenarios'],record['runs'],strict=True):
        if not scenario['accepted']:
            expected={'scenario_id':scenario['id'],'status':'DISCOVERY_REJECTED','assertions':[]}
        else:
            exact_keys(run,{'scenario_id','status','accepted','outputs','assertions'})
            require(type(run['accepted']) is bool,'EXECUTION_RECORD_DECISION_TYPE')
            exact_keys(run['outputs'],set(c['state']))
            require(all(type(x) is int for x in run['outputs'].values()),'EXECUTION_RECORD_OUTPUT_TYPE')
            assertions=[]
            for a in scenario['assertions']:
                observed=assertion_value(c,a,scenario['inputs'],run['accepted'],run['outputs'])
                passed=type(observed) is type(a['expected']) and observed==a['expected']
                assertions.append({**a,'observed':observed,'status':'PASSED' if passed else 'FAILED'})
            expected={'scenario_id':scenario['id'],'status':'PASSED' if all(a['status']=='PASSED' for a in assertions) else 'FAILED',
                      'accepted':run['accepted'],'outputs':run['outputs'],'assertions':assertions}
        require(canonical_bytes(run)==canonical_bytes(expected),'EXECUTION_RECORD_INCONSISTENT')
    return seal({'schema':'miw.execution_record_consistency.v1',**BOUNDARY,'execution_root':record['execution_root'],
                 'status':'INTERNALLY_CONSISTENT_NOT_AUTHENTICATED','source_execution':'NONE'})

def assessment_from_execution(contract:dict,source:str,text:str,target:str,run:dict) -> dict:
    c=validate_contract(contract);require(target in requirement_ids(c),'TARGET_REQUIREMENT_UNKNOWN')
    validate_execution_record(c,source,text,run)
    relevant=[(s,a) for s in run['runs'] for a in s['assertions'] if a['requirement']==target]
    failures=[{'scenario_id':s['scenario_id'],'assertion':a} for s,a in relevant if a['status']=='FAILED']
    if failures:outcome='REPRODUCED_REQUIREMENT_FAILURE'
    elif not any(s['status']!='DISCOVERY_REJECTED' for s in run['runs']):outcome='SCENARIO_REJECTED'
    elif not relevant:outcome='TARGET_NOT_EXERCISED'
    else:outcome='NO_TARGET_COUNTEREXAMPLE_FOUND'
    return seal({'schema':'miw.counterexample_assessment.v1',**BOUNDARY,'target_requirement':target,
        'execution_root':run['execution_root'],'source_sha256':run['source_sha256'],
        'feature_sha256':run['discovery']['feature_sha256'],'discovery_root':run['discovery_root'],
        'contract_root':root(c),'outcome':outcome,'failures':failures,
        'proof_claim':False,'search_scope':'Only supplied scenarios using MIW_BDD_SCALAR_V1; no AI campaign was run'},'assessment_root')

def assess_counterexample(contract:dict,source:str,text:str,target:str) -> dict:
    # Reproduction happens here. Pure record validation above is not reproduction.
    return assessment_from_execution(contract,source,text,target,run_feature(contract,source,text))

def validate_assessment_record(contract:dict,source:str,text:str,target:str,run:dict,record:dict) -> dict:
    check_seal(record,'assessment_root')
    expected=assessment_from_execution(contract,source,text,target,run)
    require(canonical_bytes(record)==canonical_bytes(expected),'COUNTEREXAMPLE_RECORD_INCONSISTENT')
    return {'status':'INTERNALLY_CONSISTENT_NOT_AUTHENTICATED','assessment_root':record['assessment_root'],
            'source_execution':'NONE',**BOUNDARY}
