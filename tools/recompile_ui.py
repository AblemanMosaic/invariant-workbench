#!/usr/bin/env python3
"""Recompile the retained Mosaic Foundry inputs into a fresh directory."""
import argparse,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/ucm'),str(ROOT/'vendor/mosaic')]
from miw.common import require,read_bytes
from mosaic_ui.foundry import compile_library

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out)
    require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS')
    compile_library(ROOT/'foundry/source',out,ROOT/'foundry/source/application.json')
    for name in ('library.py','receipt.json'):
        require(read_bytes(out/name)==read_bytes(ROOT/'foundry/generated'/name),'FOUNDRY_RECOMPILE_MISMATCH',detail=name)
    print('PASS: both retained Foundry outputs are byte-identical. This is not Windows execution.')
    return 0
if __name__=='__main__':raise SystemExit(main())
