#!/usr/bin/env python3
"""Deterministic ZIP construction from the current tree. No authority granted."""
from pathlib import Path
import argparse,hashlib,json,stat,sys,zipfile
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor/ucm'),str(ROOT/'vendor/mosaic')]
from miw.common import read_bytes,write_json,seal,digest,safe_relative,require

def build(destination:Path):
    require(not destination.resolve().is_relative_to(ROOT.resolve()),'ARCHIVE_MUST_BE_OUTSIDE_SOURCE')
    rows=[]
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file():continue
        rel=path.relative_to(ROOT).as_posix()
        require('__pycache__' not in path.parts and path.suffix!='.pyc','BYTECODE_IN_SOURCE_TREE')
        if rel=='MANIFEST.json':continue
        safe_relative(rel);data=read_bytes(path);rows.append({'path':rel,'sha256':digest(data),'bytes':len(data)})
    write_json(ROOT/'MANIFEST.json',seal({'schema':'miw.capsule_manifest.v1','standing':'INFORMATION_ONLY','authority_effect':'NONE','files':rows},'manifest_root'),replace_existing=True)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(p for p in ROOT.rglob('*') if p.is_file()):
            name=path.relative_to(ROOT).as_posix();data=read_bytes(path)
            info=zipfile.ZipInfo(name,date_time=(2026,10,26,0,0,0));info.create_system=3
            info.external_attr=(stat.S_IFREG|0o644)<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data,compresslevel=9)
    return {'path':str(destination),'sha256':digest(destination.read_bytes()),'bytes':destination.stat().st_size,'files':len(rows)+1}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(build(Path(a.out)),indent=2,sort_keys=True))
