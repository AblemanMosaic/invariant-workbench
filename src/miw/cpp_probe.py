"""Finite, compiled C++/native-source correspondence observations, not a proof."""
from __future__ import annotations
from pathlib import Path
import itertools
import shutil
import subprocess
from .common import require,seal,write_json,read_bytes,digest,BOUNDARY
from .external_build import run_command
from .contracts import expected_result
from .common import read_json

def run_probe(project:Path,out:Path,*,allow_trusted_compile:bool=False)->dict:
    require(allow_trusted_compile is True,'TRUSTED_SOURCE_EXECUTION_NOT_ADMITTED')
    require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS');out.mkdir(parents=True)
    compiler=shutil.which('g++')
    if compiler is None:
        result=seal({'schema':'miw.cpp_probe.v1',**BOUNDARY,'status':'NOT_RUN','reason':'GXX_NOT_AVAILABLE','upstream_zucchini':False})
        write_json(out/'SUMMARY.json',result);return result
    source=project/'integrations/cpp/assembly_probe.cpp';exe=out/'assembly_probe'
    argv=[compiler,'-std=c++17','-O1','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all',str(source.resolve()),'-o',str(exe.resolve())]
    compiled=run_command(argv,project,out/'compile.log')
    require(compiled['returncode']==0,'CPP_PROBE_BUILD_FAILED')
    contract=read_json(project/'examples/assembly/contract.json')
    cases=list(itertools.product(range(8),range(5),range(3),range(-2,6)))
    maximum=2**63-1
    # Include representable boundary cases and explicit machine-range rejections.
    cases.extend([(maximum,maximum,0,maximum//2),(2,1,maximum,1),(0,0,0,maximum),(-1,0,0,1),(0,0,0,-maximum)])
    data=''.join(' '.join(map(str,c))+'\n' for c in cases).encode()
    result=subprocess.run([str(exe.resolve())],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    (out/'execution.stderr').write_bytes(result.stderr);(out/'execution.stdout').write_bytes(result.stdout)
    require(result.returncode==0,'CPP_PROBE_EXECUTION_FAILED')
    observed=[tuple(map(int,l.split())) for l in result.stdout.decode().splitlines()]
    require(len(observed)==len(cases),'CPP_PROBE_RESULT_COUNT')
    domain_count=range_refusals=0
    for c,actual in zip(cases,observed):
        a,b,f,q=c
        outside=min(a,b,f)<0 or q>maximum//2 or (q>0 and a>=2*q and b>=q and f>maximum-q)
        if outside:expected=(-1,a,b,f);range_refusals+=1
        else:
            oracle=expected_result(contract,dict(zip(contract['parameters'],c)))
            expected=(int(oracle[0]),*[oracle[1][name] for name in contract['state']]);domain_count+=1
        require(actual==expected,'CPP_PROBE_DIFFERENCE',detail=str(c))
    version=subprocess.run([compiler,'--version'],capture_output=True,text=True,timeout=10).stdout.splitlines()[0]
    exe_hash=digest(read_bytes(exe));exe.unlink() # no platform binary is shipped
    record=seal({'schema':'miw.cpp_probe.v1',**BOUNDARY,'status':'PASSED_FINITE_DIFFERENTIAL_PROBE',
                 'compiler':version,'compile':compiled,'source_sha256':digest(read_bytes(source)),
                 'binary_sha256':exe_hash,'binary_distributed':False,'cases':len(cases),'matched_in_model_domain':domain_count,
                 'explicit_range_refusals':range_refusals,'undefined_behavior_sanitizer':'ENABLED_NO_DIAGNOSTICS',
                 'input_sha256':digest(data),'output_sha256':digest(result.stdout),
                 'upstream_zucchini':False,'cpp_formal_proof':False,'claim_scope':'THE_LISTED_FINITE_CASES_ONLY'})
    write_json(out/'SUMMARY.json',record);return record
