#!/usr/bin/env python3
"""Create terminal custody around one explicit MIW run-zucchini invocation."""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/ucm'),str(ROOT/'vendor/mosaic')]
from miw.common import BOUNDARY,digest,read_bytes,require,seal,write_json

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def main(argv=None) -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--custody',required=True)
    parser.add_argument('--writable-source-copy',action='store_true')
    parser.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args(argv)
    command=list(args.command)
    if command and command[0]=='--':command=command[1:]
    require(command and command[0]=='run-zucchini','WRAPPED_COMMAND_INVALID')
    custody=Path(args.custody).absolute()
    require(not custody.exists(),'CUSTODY_ALREADY_EXISTS')
    custody.mkdir(parents=True)
    child=[sys.executable,'-I','-B',str(ROOT/'tools'/'miw.py'),*command]
    terminal=custody/'TERMINAL.json'
    started=now()
    provisional=seal({'schema':'miw.external_terminal.v1',**BOUNDARY,'status':'STARTED_NO_TERMINAL',
                      'started_at':started,'completed_at':None,'command':child,'exit_code':None,
                      'stdout_sha256':None,'stderr_sha256':None},'terminal_root')
    write_json(terminal,provisional)
    source_copy_from=None
    if args.writable_source_copy:
        index=command.index('--source-directory')+1
        source_copy_from=command[index]
        copied=custody.parent/'source-work'
        require(not copied.exists(),'SOURCE_COPY_ALREADY_EXISTS')
        shutil.copytree(source_copy_from,copied)
        command[index]=str(copied)
        child=[sys.executable,'-I','-B',str(ROOT/'tools'/'miw.py'),*command]
    code=125;detail=None
    stdout=custody/'stdout.log';stderr=custody/'stderr.log'
    try:
        with stdout.open('xb') as out,stderr.open('xb') as err:
            completed=subprocess.run(child,stdout=out,stderr=err,timeout=3900)
        code=completed.returncode
    except BaseException as error:
        detail=type(error).__name__
    final=seal({'schema':'miw.external_terminal.v1',**BOUNDARY,
                'status':'COMPLETED' if detail is None else 'WRAPPER_ERROR',
                'started_at':started,'completed_at':now(),'command':child,'exit_code':code,
                'stdout_sha256':digest(read_bytes(stdout)) if stdout.is_file() else None,
                'stderr_sha256':digest(read_bytes(stderr)) if stderr.is_file() else None,
                'source_copy_from':source_copy_from,'wrapper_error':detail},'terminal_root')
    write_json(terminal,final,replace_existing=True)
    print(json.dumps({'status':final['status'],'exit_code':code,'terminal':str(terminal),
                      'terminal_root':final['terminal_root']},sort_keys=True))
    return code

if __name__=='__main__':raise SystemExit(main())
