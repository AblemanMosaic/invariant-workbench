#!/usr/bin/env python3
"""Actual Mosaic Win32 smoke witness, with explicit NOT_RUN on other hosts."""
from pathlib import Path
import argparse,sys,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/ucm'),str(ROOT/'vendor/mosaic')]
from miw.foundry_view import native_smoke
from miw.common import write_json,require

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory');p.add_argument('--out',required=True);a=p.parse_args()
    require(not Path(a.out).exists(),'OUTPUT_ALREADY_EXISTS')
    record=native_smoke(Path(a.directory) if a.directory else None)
    write_json(Path(a.out),record);print(json.dumps(record,indent=2))
    return 0 if record['status']=='PASSED_REAL_WIN32_SMOKE' else 6
if __name__=='__main__':raise SystemExit(main())
