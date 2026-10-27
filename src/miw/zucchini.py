"""Read-only Zucchini report 2.2.0 adapter and explicitly caller-bound JUnit.

An independently implemented strict support profile, not an upstream build,
full JSON Schema implementation or proof of a C++ step definition. No report
paths, regexes, source snippets or schema URLs are executed or followed.
"""
from __future__ import annotations
import xml.etree.ElementTree as ET
from copy import deepcopy
import re
from typing import Any
from .common import BOUNDARY, Refusal, require, strict_loads, digest, seal, root, exact_keys, check_seal

SUPPORTED='2.2.0'
SCHEMA_URL='https://raw.githubusercontent.com/AnarchoSystems/Zucchini/main/schemas/rules-report.v2.2.0.schema.json'

def _obj(x,fields,label):
    require(type(x) is dict,'ZUCCHINI_OBJECT_REQUIRED',detail=label)
    require(set(fields)<=set(x),'ZUCCHINI_REQUIRED_FIELD_MISSING',detail=label)
    for k,t in fields.items():
        if isinstance(t,tuple): require(type(x[k]) in t,'ZUCCHINI_FIELD_TYPE',detail=label+'.'+k)
        else: require(type(x[k]) is t,'ZUCCHINI_FIELD_TYPE',detail=label+'.'+k)
    return x

def _int(x,label):require(type(x) is int and x>=0,'ZUCCHINI_NONNEGATIVE_INTEGER_REQUIRED',detail=label)
def _enum(x,allowed,label):require(type(x) is str and x in allowed,'ZUCCHINI_ENUM_INVALID',detail=label)
def _strings(x,label):require(type(x) is list and all(type(s) is str for s in x),'ZUCCHINI_STRING_ARRAY_REQUIRED',detail=label)
def _unique(xs,label):require(len(xs)==len(set(xs)),'ZUCCHINI_DUPLICATE_IDENTITY',detail=label)

def _scenario_name_matches(event_name:str,scenario_name:str) -> bool:
    if event_name==scenario_name:return True
    match=re.fullmatch(r'(.+) #([2-9][0-9]*)',scenario_name)
    return match is not None and match.group(1)==event_name

def _cell(value):
    _obj(value,{'row':int},'cell');_int(value['row'],'cell.row')
    for k in ('line','column'):
        if k in value:_int(value[k],'cell.'+k)
    if 'key' in value:require(type(value['key']) is str,'ZUCCHINI_CELL_KEY_INVALID')

def _step(step):
    _obj(step,{'regex':str,'methodName':str,'text':str,'line':int,'column':int,'captures':list,'argument':(dict,type(None))},'step')
    _int(step['line'],'step.line');_int(step['column'],'step.column')
    if 'keywordType' in step:_enum(step['keywordType'],{'context','action','outcome'},'keywordType')
    for c in step['captures']:_obj(c,{'name':str,'value':(bool,int,str)},'capture')
    a=step['argument']
    if a is not None:
        if a.get('kind')=='docString':
            _obj(a,{'kind':str,'content':str},'argument')
            if 'mediaType' in a:require(type(a['mediaType']) is str,'ZUCCHINI_ARGUMENT_INVALID')
        elif a.get('kind')=='dataTable':
            _obj(a,{'kind':str,'rows':list},'argument')
            require(all(type(r) in (dict,list) for r in a['rows']),'ZUCCHINI_TABLE_INVALID')
            if 'ignoredKeys' in a:_strings(a['ignoredKeys'],'ignoredKeys')
            if 'cellLocations' in a:
                require(type(a['cellLocations']) is list and all(type(r) in (dict,list) for r in a['cellLocations']),
                        'ZUCCHINI_TABLE_LOCATIONS_INVALID')
        else:raise Refusal('ZUCCHINI_ARGUMENT_KIND_UNSUPPORTED')

def validate_report(raw:bytes) -> dict:
    require(type(raw) is bytes and len(raw)<=8*1024*1024,'ZUCCHINI_INPUT_LIMIT')
    r=strict_loads(raw)
    _obj(r,{'schema_version':str,'fixture':str,'feature_directory':str,'build_id':str,'discovery_id':str,
        'discovered_at_ms':int,'discovery_success':bool,'discovery_diagnostics':list,'rules':list,'scenarios':list,'sources':dict},'report')
    require(r['schema_version']==SUPPORTED,'ZUCCHINI_VERSION_UNSUPPORTED')
    if '$schema' in r:require(r['$schema']==SCHEMA_URL,'ZUCCHINI_SCHEMA_REFERENCE_MISMATCH')
    if 'executable' in r:require(type(r['executable']) is str,'ZUCCHINI_EXECUTABLE_INVALID')
    _int(r['discovered_at_ms'],'discovered_at_ms')
    require(len(r['scenarios'])<=10_000 and len(r['rules'])<=2_000,'ZUCCHINI_RECORD_LIMIT')
    for diagnostic in r['discovery_diagnostics']:
        _obj(diagnostic,{'message':str,'severity':str},'diagnostic')
        _enum(diagnostic['severity'],{'error','warning','info'},'severity')
    for path,lines in r['sources'].items():
        require(type(path) is str,'ZUCCHINI_SOURCE_KEY_INVALID');_strings(lines,'sources')
    scenarios={}
    for s in r['scenarios']:
        _obj(s,{'id':int,'name':str,'feature':str,'gherkin_rule':str,'uri':str,'line':int,'tags':list,
            'steps':list,'test_name':str,'plan_fingerprint':str,'result_key':str,'accepted':bool},'scenario')
        _int(s['id'],'scenario.id');_int(s['line'],'scenario.line');_strings(s['tags'],'scenario.tags')
        require(s['id'] not in scenarios,'ZUCCHINI_DUPLICATE_IDENTITY',detail='scenario.id');scenarios[s['id']]=s
        if s['accepted']:
            require(bool(s['test_name']) and bool(s['result_key']) and bool(s['plan_fingerprint']),
                    'ZUCCHINI_EXECUTION_IDENTITY_EMPTY')
        for step in s['steps']:_step(step)
        if 'feature_relative_path' in s:require(type(s['feature_relative_path']) is str,'ZUCCHINI_RELATIVE_PATH_TYPE')
        if 'asserted_facts' in s:_int(s['asserted_facts'],'asserted_facts')
        if 'unjustified_facts' in s:
            require(type(s['unjustified_facts']) is list,'ZUCCHINI_ASSERTED_FACTS_INVALID')
            for fact in s['unjustified_facts']:
                _obj(fact,{'step_index':int,'line':int,'column':int},'asserted_fact')
                for k in ('step_index','line','column'):_int(fact[k],k)
                require(fact['step_index']<len(s['steps']),'ZUCCHINI_ASSERTION_REFERENCE_INVALID')
                if 'cell' in fact:
                    _cell(fact['cell']);require('key' in fact['cell'],'ZUCCHINI_CELL_KEY_REQUIRED')
    _unique([s['test_name'] for s in r['scenarios'] if s['test_name']],'test_name')
    _unique([s['result_key'] for s in r['scenarios'] if s['result_key']],'result_key')
    _unique([rule.get('name') for rule in r['rules'] if type(rule) is dict and type(rule.get('name')) is str],'rule.name')
    for rule in r['rules']:
        _obj(rule,{'name':str,'description':str,'kind':str,'requirements':list,'events':list},'rule')
        require(bool(rule['name']),'ZUCCHINI_RULE_NAME_EMPTY');_enum(rule['kind'],{'business','dsl'},'rule.kind')
        requirements={};values=[]
        for q in rule['requirements']:
            _obj(q,{'tag':str,'description':str,'value':int},'requirement')
            require(q['tag'] and q['tag'] not in requirements,'ZUCCHINI_REQUIREMENT_ID_INVALID')
            requirements[q['tag']]=q;values.append(q['value'])
            if 'strictness' in q:_enum(q['strictness'],{'unspecified','exact','one_of','bounded','open_ended'},'strictness')
        _unique(values,'requirement.value')
        for e in rule['events']:
            _obj(e,{'kind':str,'tag':str,'message':str,'scenario':str,'feature':str,'gherkin_rule':str,
                'scenario_line':int,'scenario_tags':list,'uri':str,'line':int,'column':int,'step':str,
                'scenario_id':int,'test_name':str,'scenario_accepted':bool},'event')
            _enum(e['kind'],{'coverage','violation'},'event.kind')
            require(e['tag'] in requirements,'ZUCCHINI_EVENT_REQUIREMENT_UNKNOWN')
            require(e['scenario_id'] in scenarios,'ZUCCHINI_EVENT_SCENARIO_UNKNOWN')
            s=scenarios[e['scenario_id']]
            require(_scenario_name_matches(e['scenario'],s['name']),'ZUCCHINI_EVENT_IDENTITY_MISMATCH')
            pairs=[('feature','feature'),('gherkin_rule','gherkin_rule'),('scenario_line','line'),
                   ('scenario_tags','tags'),('uri','uri'),('test_name','test_name'),('scenario_accepted','accepted')]
            require(all(type(e[a]) is type(s[b]) and e[a]==s[b] for a,b in pairs),'ZUCCHINI_EVENT_IDENTITY_MISMATCH')
            for k in ('line','column','scenario_line','scenario_id'):_int(e[k],k)
            if e['kind']=='violation':
                require('severity' in e,'ZUCCHINI_VIOLATION_SEVERITY_REQUIRED')
            if 'severity' in e:_enum(e['severity'],{'error','warning','info'},'severity')
            if e['kind']=='coverage':
                matching=[step for step in s['steps'] if step['line']==e['line'] and step['column']==e['column'] and step['text']==e['step']]
                require(len(matching)==1,'ZUCCHINI_COVERAGE_STEP_UNRESOLVED')
            if 'cell' in e:
                _cell(e['cell'])
                if e['kind']=='coverage':
                    cell=e['cell'];arg=matching[0]['argument']
                    require(type(arg) is dict and arg.get('kind')=='dataTable' and 'key' in cell,
                            'ZUCCHINI_COVERAGE_CELL_UNRESOLVED')
                    require(cell['row']<len(arg['rows']),'ZUCCHINI_COVERAGE_CELL_UNRESOLVED')
                    row=arg['rows'][cell['row']];key=cell['key']
                    exists=(key in row) if type(row) is dict else (key.isdigit() and int(key)<len(row))
                    require(exists and key not in arg.get('ignoredKeys',[]),'ZUCCHINI_COVERAGE_CELL_UNRESOLVED')
    if 'assertion_justification' in r:
        a=r['assertion_justification']
        _obj(a,{'enforced':bool,'scenarios':int,'asserted_facts':int,'unjustified_facts':int},'assertion_justification')
        for k in ('scenarios','asserted_facts','unjustified_facts','scenarios_without_assertions','scenarios_over_limit','max_unjustified_facts_per_scenario'):
            if k in a:_int(a[k],k)
        if a['enforced']:
            require(all(k in a for k in ('severity','max_unjustified_facts_per_scenario','scenarios_without_assertions','scenarios_over_limit')),
                    'ZUCCHINI_LEGACY_ENFORCEMENT_FIELDS_MISSING')
        if 'severity' in a:_enum(a['severity'],{'error','warning','info'},'severity')
    return r

def import_report(raw:bytes) -> dict:
    r=validate_report(raw);requirements=[]
    for rule in r['rules']:
        for q in rule['requirements']:
            coverage=[e for e in rule['events'] if e['tag']==q['tag'] and e['kind']=='coverage']
            eligible=[e for e in coverage if e['scenario_accepted'] and rule['kind']=='business']
            requirements.append({'rule':rule['name'],'kind':rule['kind'],'tag':q['tag'],'description':q['description'],
                'strictness':q.get('strictness','unspecified'),
                'covered_scenarios':sorted({e['scenario_id'] for e in eligible}),
                'declared_events':coverage,'execution_status':'NOT_IMPORTED',
                'proof_status':'NOT_PROVED','failure_attribution':'NOT_ESTABLISHED'})
    return seal({'schema':'miw.zucchini_import.v1',**BOUNDARY,'report_sha256':digest(raw),
        'fixture':r['fixture'],'executable':r.get('executable'), 'build_id':r['build_id'],'discovery_id':r['discovery_id'],
        'discovery_success':r['discovery_success'],'requirements':requirements,'raw_report':r,
        'source_authenticity':'UNATTESTED_IMPORTED_DATA','source_execution':'NONE',
        'unknown_fields':'PRESERVED_IN_RAW_REPORT_NOT_INTERPRETED',
        'claim':'Declared scenario coverage only; neither execution nor proof'},'import_root')

def parse_junit(raw:bytes) -> dict:
    """A bounded CTest/GoogleTest-compatible record profile, not all JUnit dialects.

    Unknown explicit states and contradictory counters refuse. Missing testcase
    outcome markers mean conventional JUnit success only within this profile.
    Hashes and well-formed records do not authenticate their producer.
    """
    require(type(raw) is bytes and len(raw)<=8*1024*1024,'JUNIT_INPUT_LIMIT')
    try:text=raw.decode('utf-8')
    except UnicodeError as e:raise Refusal('JUNIT_UTF8_REQUIRED') from e
    require('\x00' not in text,'JUNIT_UTF8_REQUIRED')
    upper=text.upper();require('<!DOCTYPE' not in upper and '<!ENTITY' not in upper,'JUNIT_DTD_FORBIDDEN')
    encoding=re.search(r'<\?xml[^>]*encoding=["\']([^"\']+)',text,re.IGNORECASE)
    require(encoding is None or encoding.group(1).lower() in ('utf-8','us-ascii'),'JUNIT_UTF8_REQUIRED')
    try:tree=ET.fromstring(text)
    except (ET.ParseError,ValueError,RecursionError) as e:raise Refusal('JUNIT_PARSE_FAILED') from e
    require(tree.tag in ('testsuites','testsuite'),'JUNIT_ROOT_UNSUPPORTED')
    nodes=list(tree.iter());require(len(nodes)<=100_000,'JUNIT_NODE_LIMIT')
    parents={child:parent for parent in nodes for child in parent}
    tests={};kinds={}
    statuses={None,'run','passed','pass','failed','fail','error','notrun','disabled','skipped','skip'}
    results={None,'completed','suppressed','skipped'}
    for item in nodes:
        if item.tag!='testcase':continue
        require(parents[item].tag=='testsuite','JUNIT_TESTCASE_LOCATION_INVALID')
        name=item.attrib.get('name');require(type(name) is str and name and name not in tests,'JUNIT_TEST_ID_INVALID')
        declared=item.attrib.get('status');result=item.attrib.get('result')
        require(declared in statuses and result in results,'JUNIT_STATUS_UNSUPPORTED')
        children=[x.tag for x in item]
        require(all(children.count(k)<=1 for k in ('failure','error','skipped')),'JUNIT_DUPLICATE_OUTCOME')
        failure='failure' in children or declared in ('fail','failed')
        error='error' in children or declared=='error'
        skipped='skipped' in children or declared in ('skip','skipped') or result=='skipped'
        notrun=declared in ('notrun','disabled') or result=='suppressed'
        require(not(failure and error),'JUNIT_CONTRADICTORY_STATUS')
        require(not((failure or error) and (skipped or notrun)),'JUNIT_CONTRADICTORY_STATUS')
        require(not(declared in ('pass','passed') and (failure or error or skipped or notrun)), 'JUNIT_CONTRADICTORY_STATUS')
        require(not(result=='suppressed' and skipped),'JUNIT_CONTRADICTORY_STATUS')
        require(not(result=='completed' and notrun),'JUNIT_CONTRADICTORY_STATUS')
        status='FAILED' if failure or error else 'SKIPPED' if skipped else 'NOT_RUN' if notrun else 'PASSED'
        tests[name]={'status':status,'classname':item.attrib.get('classname','')}
        kinds[item]={'tests':1,'failures':int(failure),'errors':int(error),
                     'skipped':int(status=='SKIPPED'),'disabled':int(status=='NOT_RUN')}
    require(bool(tests),'JUNIT_NO_TESTCASES')
    for suite in (n for n in nodes if n.tag in ('testsuite','testsuites')):
        if suite is not tree:
            require(parents[suite].tag in ('testsuite','testsuites'),'JUNIT_SUITE_LOCATION_INVALID')
        require(not any(child.tag in ('failure','error','skipped') for child in suite), 'JUNIT_UNATTRIBUTED_SUITE_OUTCOME')
        cases=[kinds[n] for n in suite.iter('testcase')]
        for key in ('tests','failures','errors','skipped','disabled'):
            if key not in suite.attrib:continue
            value=suite.attrib[key]
            require(re.fullmatch(r'[0-9]{1,9}',value) is not None,'JUNIT_COUNTER_INVALID')
            require(int(value)==sum(c[key] for c in cases),'JUNIT_COUNTER_MISMATCH',detail=key)
    return {'junit_sha256':digest(raw),'tests':tests,'profile':'MIW_BOUNDED_CTEST_GTEST_JUNIT'}

def make_junit_binding(report_raw:bytes,junit_raw:bytes) -> dict:
    r=validate_report(report_raw);j=parse_junit(junit_raw)
    return seal({'schema':'miw.junit_binding.v1','report_sha256':digest(report_raw),'junit_sha256':j['junit_sha256'],
        'build_id':r['build_id'],'discovery_id':r['discovery_id'],
        'association':'CALLER_ASSERTED_SAME_BUILD_NOT_ATTESTED',**BOUNDARY},'binding_root')

def link_junit(report_raw:bytes,junit_raw:bytes,binding:dict) -> dict:
    imported=import_report(report_raw);j=parse_junit(junit_raw)
    expected=make_junit_binding(report_raw,junit_raw)
    require(binding==expected,'JUNIT_BINDING_MISMATCH')
    scenario_runs=[];matched=set()
    for s in imported['raw_report']['scenarios']:
        expected={s['test_name'],f"{imported['fixture']}.{s['test_name']}"}
        candidates=[]
        for junit_name,value in j['tests'].items():
            base=junit_name.split('  # GetParam() = ',1)[0]
            if base in expected:candidates.append((junit_name,value))
        require(len(candidates)<=1,'JUNIT_TEST_ID_AMBIGUOUS',detail=s['test_name'])
        junit_name,observation=candidates[0] if candidates else (None,None)
        if observation:matched.add(junit_name)
        if not s['accepted']:
            status='DISCOVERY_REJECTED'
        elif observation is None:status='NOT_RUN'
        else:status=observation['status']
        scenario_runs.append({'scenario_id':s['id'],'test_name':s['test_name'],'junit_test_name':junit_name,'status':status})
    by_id={s['scenario_id']:s for s in scenario_runs};matrix=[]
    for q in imported['requirements']:
        statuses=[by_id[i]['status'] for i in q['covered_scenarios']]
        matrix.append({**q,'execution_statuses':statuses,'execution_status':'IMPORTED_TEST_OBSERVATIONS',
                       'counterexample_status':'NOT_ESTABLISHED_FROM_SCENARIO_STATUS'})
    return seal({'schema':'miw.zucchini_execution_link.v1',**BOUNDARY,'import_root':imported['import_root'],
        'binding':binding,'scenario_runs':scenario_runs,'requirements':matrix,
        'unmatched_junit_tests':sorted(set(j['tests'])-matched),'association':'CALLER_ASSERTED_SAME_BUILD_NOT_ATTESTED',
        'proof_status':'NOT_PROVED','failure_attribution':'NOT_ESTABLISHED',
        'claim':'JUnit statuses linked by exact test name under an explicit, unauthenticated caller binding'},'link_root')
