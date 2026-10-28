#!/usr/bin/env python3
"""Standard-library-only capsule byte verifier. Does not import candidate code.

PASS means exact expected transport and closed-world file integrity. It is not
semantic qualification, signature authentication, proof replay or release.
"""
from __future__ import annotations
import argparse,hashlib,json,zipfile,stat,io
from pathlib import Path,PurePosixPath

MAX_EXPANDED=128*1024*1024

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def sha(data):return hashlib.sha256(data).hexdigest()
def require(x,code):
    if not x:raise ValueError(code)
def pairs(rows):
    d={}
    for k,v in rows:
        require(k not in d,'DUPLICATE_JSON_KEY');d[k]=v
    return d
def reject(x):raise ValueError('NONFINITE_OR_FLOAT_JSON')
def load(data):return json.loads(data.decode('utf-8'),object_pairs_hook=pairs,parse_constant=reject,parse_float=reject)
def safe(name):
    require(type(name) is str and name and len(name)<=240 and '\\' not in name and ':' not in name and '\x00' not in name,'UNSAFE_MEMBER')
    require(not PurePosixPath(name).is_absolute() and all(x not in ('','.','..') and not x.endswith((' ','.')) for x in name.split('/')),'UNSAFE_MEMBER')

def manifest_rows(m):
    require(set(m)=={'schema','standing','authority_effect','files','manifest_root'},'MANIFEST_SHAPE_INVALID')
    require(m['schema']=='miw.capsule_manifest.v1' and m['standing']=='INFORMATION_ONLY' and m['authority_effect']=='NONE','MANIFEST_BOUNDARY_INVALID')
    require(m['manifest_root']==sha(canonical({k:v for k,v in m.items() if k!='manifest_root'})),'MANIFEST_ROOT_MISMATCH')
    rows=m['files'];require(type(rows) is list,'MANIFEST_ROWS_INVALID')
    paths=[]
    for r in rows:
        require(type(r) is dict and set(r)=={'path','sha256','bytes'},'MANIFEST_ROW_INVALID')
        safe(r['path']);paths.append(r['path'])
        require(type(r['bytes']) is int and r['bytes']>=0,'MANIFEST_MEMBER_INVALID')
        require(type(r['sha256']) is str and len(r['sha256'])==64 and all(c in '0123456789abcdef' for c in r['sha256']),'MANIFEST_MEMBER_INVALID')
    require(len(paths)==len(set(paths))==len({p.casefold() for p in paths}),'DUPLICATE_OR_CASE_COLLIDING_MEMBERS')
    return rows

def verify(path:Path,expected_sha256:str):
    require(len(expected_sha256)==64 and all(c in '0123456789abcdef' for c in expected_sha256),'EXTERNAL_SHA256_REQUIRED')
    require(path.stat().st_size<=MAX_EXPANDED,'TRANSPORT_SIZE_LIMIT')
    data=path.read_bytes();require(sha(data)==expected_sha256,'TRANSPORT_SHA256_MISMATCH')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist();names=[i.filename for i in infos]
        require(len(names)==len(set(names))==len({n.casefold() for n in names}),'DUPLICATE_OR_CASE_COLLIDING_MEMBERS')
        require(sum(i.file_size for i in infos)<=MAX_EXPANDED,'EXPANDED_SIZE_LIMIT')
        require(len(names)<=8192,'MEMBER_COUNT_LIMIT')
        for i in infos:
            safe(i.filename);mode=(i.external_attr>>16)&0xffff
            require(not i.is_dir() and not i.flag_bits&1,'DIRECTORY_OR_ENCRYPTION_UNSUPPORTED')
            require(stat.S_IFMT(mode) in (0,stat.S_IFREG),'NONREGULAR_ARCHIVE_MEMBER')
            require(not i.filename.endswith('.pyc') and '__pycache__' not in PurePosixPath(i.filename).parts,'BYTECODE_FORBIDDEN')
        require('MANIFEST.json' in names,'MANIFEST_REQUIRED')
        m=load(z.read('MANIFEST.json'));rows=manifest_rows(m)
        require(len(rows)==len(names)-1,'MANIFEST_COUNT_MISMATCH')
        paths=[]
        for r in rows:
            paths.append(r['path']);require(r['path'] in names,'MANIFEST_MEMBER_INVALID')
            b=z.read(r['path']);require(len(b)==r['bytes'] and sha(b)==r['sha256'],'MEMBER_DIGEST_MISMATCH')
        require(len(paths)==len(set(paths)) and set(paths)==set(names)-{'MANIFEST.json'},'CLOSED_WORLD_MEMBER_MISMATCH')
        return {'status':'PASS_BYTE_INTEGRITY_ONLY','archive_sha256':expected_sha256,'manifest_root':m['manifest_root'],
                'file_count':len(names),'expanded_bytes':sum(i.file_size for i in infos),
                'candidate_imports':0,'subject_program_execution':'NONE','standing':'INFORMATION_ONLY','authority_effect':'NONE'}

def verify_directory(path:Path):
    require(path.exists() and path.is_dir() and not path.is_symlink(),'DIRECTORY_REQUIRED')
    root=path.resolve();manifest_path=root/'MANIFEST.json'
    require(manifest_path.is_file() and not manifest_path.is_symlink(),'MANIFEST_REQUIRED')
    manifest_data=manifest_path.read_bytes();require(len(manifest_data)<=MAX_EXPANDED,'MANIFEST_SIZE_LIMIT')
    m=load(manifest_data);rows=manifest_rows(m)
    declared={r['path']:r for r in rows};actual={}
    total=0
    for candidate in root.rglob('*'):
        rel=candidate.relative_to(root).as_posix();parts=PurePosixPath(rel).parts
        if parts and parts[0]=='.git':continue
        require(not candidate.is_symlink(),'NONREGULAR_DIRECTORY_MEMBER')
        if candidate.is_dir():continue
        mode=candidate.stat().st_mode;require(stat.S_ISREG(mode),'NONREGULAR_DIRECTORY_MEMBER')
        safe(rel);require(rel not in actual and rel.casefold() not in {p.casefold() for p in actual},'DUPLICATE_OR_CASE_COLLIDING_MEMBERS')
        require(not rel.endswith('.pyc') and '__pycache__' not in parts,'BYTECODE_FORBIDDEN')
        data=candidate.read_bytes();total+=len(data);require(total<=MAX_EXPANDED,'EXPANDED_SIZE_LIMIT')
        actual[rel]=(len(data),sha(data))
    require(len(actual)<=8192,'MEMBER_COUNT_LIMIT')
    require(set(actual)==set(declared)|{'MANIFEST.json'},'CLOSED_WORLD_MEMBER_MISMATCH')
    for rel,row in declared.items():
        size,digest=actual[rel];require(size==row['bytes'] and digest==row['sha256'],'MEMBER_DIGEST_MISMATCH')
    return {'status':'PASS_DIRECTORY_BYTE_INTEGRITY_ONLY','manifest_root':m['manifest_root'],
            'file_count':len(actual),'expanded_bytes':total,'ignored_paths':['.git/'],
            'candidate_imports':0,'subject_program_execution':'NONE','standing':'INFORMATION_ONLY','authority_effect':'NONE'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',nargs='?');p.add_argument('--sha256');p.add_argument('--directory');a=p.parse_args()
    if bool(a.archive)==bool(a.directory):p.error('provide exactly one archive or --directory')
    if a.archive and not a.sha256:p.error('--sha256 is required for archive verification')
    if a.directory and a.sha256:p.error('--sha256 applies only to archive verification')
    try:
        result=verify(Path(a.archive),a.sha256) if a.archive else verify_directory(Path(a.directory))
        print(json.dumps(result,sort_keys=True,indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile,UnicodeError) as e:
        print(json.dumps({'status':'REFUSED','detail':str(e),'authority_effect':'NONE'}));return 2
if __name__=='__main__':raise SystemExit(main())
