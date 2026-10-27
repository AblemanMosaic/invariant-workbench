"""Explicitly admitted local CMake build, no automatic dependency downloads.

This is an execution adapter, NOT an OS sandbox. Never use on untrusted source
without an external isolation boundary. It does not invent an upstream run.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from .common import require,Refusal,read_bytes,write_json,seal,digest,BOUNDARY
from .common import safe_relative
from .governance import snapshot
from .zucchini import import_report,make_junit_binding,link_junit,parse_junit

ALLOWED_CMAKE_DEFINITIONS={
    'CMAKE_PROJECT_TOP_LEVEL_INCLUDES',
    'MIW_CPM_MODULE',
    'CPM_cucumber_messages_SOURCE',
    'CPM_nlohmann_json_SOURCE',
    'ZUCCHINI_CUCUMBER_GHERKIN_SOURCE_DIR',
    'ZUCCHINI_GOOGLETEST_SOURCE_DIR',
    'ZUCCHINI_FETCH_TPP',
    'ZUCCHINI_LIBFYAML_SOURCE_DIR',
    'ZUCCHINI_NLOHMANN_JSON_SCHEMA_VALIDATOR_SOURCE_DIR',
    'ZUCCHINI_NLOHMANN_JSON_SOURCE_DIR',
    'ZUCCHINI_TPP_BIN_DIR',
}

def _configure_definitions(values:list[str]) -> list[str]:
    require(type(values) is list and all(type(v) is str for v in values),'CMAKE_DEFINITIONS_INVALID')
    parsed={}
    for value in values:
        require('=' in value and '\x00' not in value and '\n' not in value and len(value)<=2048,
                'CMAKE_DEFINITION_INVALID')
        key,setting=value.split('=',1)
        require(key in ALLOWED_CMAKE_DEFINITIONS and bool(setting) and key not in parsed,
                'CMAKE_DEFINITION_NOT_ALLOWED',detail=key)
        parsed[key]=setting
    return [f'-D{key}={parsed[key]}' for key in sorted(parsed)]

def preflight()->dict:
    tools={k:shutil.which(k) for k in ('cmake','ctest','c++','psql','postgres','initdb')}
    return seal({'schema':'miw.external_preflight.v1',**BOUNDARY,'tools':tools,
                 'upstream_zucchini':'NOT_SUPPLIED_OR_BUILT','postgres_live':'NOT_RUN',
                 'network_access':'NOT_REQUIRED_BY_REPLAY','missing_tools':[k for k,v in tools.items() if v is None]})

def run_command(argv:list[str],cwd:Path,log:Path,*,timeout:int=180)->dict:
    require(type(argv) is list and argv and all(type(a) is str for a in argv),'BUILD_COMMAND_INVALID')
    require(type(timeout) is int and 1<=timeout<=3600,'BUILD_TIMEOUT_INVALID')
    log.parent.mkdir(parents=True,exist_ok=True);started=time.monotonic();timed_out=False
    with log.open('wb') as stream:
        process=subprocess.Popen(argv,cwd=cwd,stdout=stream,stderr=subprocess.STDOUT,
                                 start_new_session=(os.name!='nt'))
        try:code=process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True
            if os.name!='nt':
                import signal
                os.killpg(process.pid,signal.SIGKILL)
            else:process.kill()
            code=process.wait()
    size=log.stat().st_size
    require(size<=8*1024*1024,'BUILD_LOG_SIZE_LIMIT')
    return {'argv':argv,'returncode':code,'timed_out':timed_out,'elapsed_ms':int((time.monotonic()-started)*1000),
            'log_sha256':digest(read_bytes(log)),'log':log.name}

def run_zucchini(source:Path,out:Path,*,expected_source_root:str,upstream_commit:str,
                  build_config:str='Release',generator:str|None=None,
                  cmake_definitions:list[str]|None=None,accept_report_paths:list[str]|None=None,
                  step_timeout:int=600,
                  allow_trusted_build:bool=False)->dict:
    require(allow_trusted_build is True,'TRUSTED_SOURCE_EXECUTION_NOT_ADMITTED')
    require(type(upstream_commit) is str and re.fullmatch(r'[0-9a-f]{40}',upstream_commit) is not None,
            'UPSTREAM_COMMIT_INVALID')
    require(type(build_config) is str and re.fullmatch(r'[A-Za-z0-9_.-]{1,32}',build_config) is not None,
            'BUILD_CONFIG_INVALID')
    require(generator is None or (type(generator) is str and re.fullmatch(r'[A-Za-z0-9 _+.-]{1,64}',generator) is not None),
            'CMAKE_GENERATOR_INVALID')
    require(type(step_timeout) is int and 1<=step_timeout<=3600,'BUILD_TIMEOUT_INVALID')
    definitions=_configure_definitions(cmake_definitions or [])
    acceptance_paths=sorted(safe_relative(value) for value in (accept_report_paths or []))
    require(len(acceptance_paths)==len(set(acceptance_paths)),'ACCEPTANCE_REPORT_DUPLICATE')
    before=snapshot(source);require(before['snapshot_root']==expected_source_root,'UPSTREAM_SOURCE_PIN_MISMATCH')
    require((source/'CMakeLists.txt').is_file(),'UPSTREAM_CMAKE_MISSING')
    require(not out.exists() and not out.resolve().is_relative_to(source.resolve()),'BUILD_OUTPUT_INVALID')
    require(shutil.which('cmake') and shutil.which('ctest'),'CMAKE_TOOLCHAIN_MISSING')
    out.mkdir(parents=True);build=out/'build';steps=[]
    configure=['cmake','-S',str(source.resolve()),'-B',str(build.resolve()),
               f'-DCMAKE_BUILD_TYPE={build_config}','-DZUCCHINI_BUILD_TESTS=ON',
               '-DZUCCHINI_FETCH_DEPENDENCIES=OFF',*definitions]
    if generator is not None:configure.extend(['-G',generator])
    commands=[('configure',configure),
              ('build',['cmake','--build',str(build.resolve()),'--config',build_config,'--parallel','2']),
              ('test',['ctest','--test-dir',str(build.resolve()),'-C',build_config,'--parallel','2',
                       '--output-junit',str((out/'ctest.xml').resolve()),'--output-on-failure','--no-tests=error'])]
    for name,argv in commands:
        observed=run_command(argv,out,out/(name+'.log'),timeout=step_timeout);steps.append(observed)
        if observed['returncode']!=0:
            # A deliberately failing upstream example may make CTest nonzero;
            # retain that run without converting it into a blanket PASS.
            break
    stable=snapshot(source)==before;require(stable,'UPSTREAM_SOURCE_CHANGED_DURING_RUN')
    imports=[]
    if build.exists():
        for p in sorted(build.rglob('*.json'),key=lambda item:item.relative_to(build).as_posix()):
            if p.is_symlink() or p.stat().st_size>8*1024*1024:continue
            raw=read_bytes(p)
            if b'"schema_version"' not in raw or b'"discovery_id"' not in raw:continue
            try:
                imported=import_report(raw)
                result={'report_path':p.relative_to(build).as_posix(),'import':imported}
                if (out/'ctest.xml').exists():
                    junit=read_bytes(out/'ctest.xml');binding=make_junit_binding(raw,junit)
                    result['linked_execution']=link_junit(raw,junit,binding)
                imports.append(result)
            except Refusal as error:imports.append({'report_path':p.relative_to(build).as_posix(),'status':'REFUSED','code':error.code})
    junit_observation=None;junit_refusal=None
    if (out/'ctest.xml').exists():
        try:junit_observation=parse_junit(read_bytes(out/'ctest.xml'))
        except Refusal as error:junit_refusal=error.code
    supported=[r for r in imports if 'import' in r]
    observed_paths={r['report_path'] for r in imports}
    missing_acceptance=sorted(set(acceptance_paths)-observed_paths)
    selected=[r for r in imports if r['report_path'] in acceptance_paths] if acceptance_paths else supported
    executed=sum(s['status'] in ('PASSED','FAILED') for r in selected if 'import' in r
                 for s in r.get('linked_execution',{}).get('scenario_runs',[]))
    selected_refused=sum(r.get('status')=='REFUSED' for r in selected)
    refused=sum(r.get('status')=='REFUSED' for r in imports)
    if len(steps)<3:status='BUILD_INCOMPLETE'
    elif missing_acceptance:status='BUILD_OBSERVED_ACCEPTANCE_REPORT_MISSING'
    elif not selected:status='BUILD_OBSERVED_NO_SUPPORTED_REPORTS'
    elif selected_refused:status='BUILD_OBSERVED_ACCEPTANCE_REPORT_REFUSAL'
    elif executed==0:status='BUILD_OBSERVED_NO_MATCHED_EXECUTIONS'
    else:status='OBSERVED_LOCAL_BUILD'
    result=seal({'schema':'miw.zucchini_build_observation.v1',**BOUNDARY,'source_root':expected_source_root,
                 'source_unchanged':stable,'upstream_commit':upstream_commit,'build_config':build_config,
                 'generator':generator or 'CMAKE_DEFAULT','cmake_definitions':definitions,
                 'acceptance_report_paths':acceptance_paths,'missing_acceptance_reports':missing_acceptance,
                 'commands':steps,'reports':imports,'status':status,
                 'supported_reports':len(supported),'matched_executions':executed,
                 'observed_report_refusals':refused,
                 'successful_acceptance':status=='OBSERVED_LOCAL_BUILD' and junit_observation is not None and
                     all(x['returncode']==0 for x in steps) and
                     all(x['status']!='FAILED' for x in junit_observation['tests'].values()) and
                     all(r['import']['discovery_success'] and all(s['status']=='PASSED' for s in r['linked_execution']['scenario_runs']) for r in selected),
                 'junit_observation':junit_observation,'junit_refusal':junit_refusal,
                 'provenance':'LOCAL_RUNNER_OBSERVATION_NOT_INDEPENDENT_AUTHENTICATION',
                 'operating_system_sandbox':'EXTERNAL_REQUIRED_FOR_UNTRUSTED_CODE',
                 'dependency_fetch_policy':'REQUESTED_OFF_BY_CMAKE_FLAG_NOT_NETWORK_ISOLATION',
                 'source_pin_kind':'CALLER_HELD_TREE_ROOT_AND_GIT_COMMIT','proof_claim':False})
    write_json(out/'SUMMARY.json',result);return result
