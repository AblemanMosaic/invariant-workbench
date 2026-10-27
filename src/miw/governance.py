"""Local verification-basis snapshots and exact candidate-diff checks.

This is an information-only constraint checker, not UCM signed work-manager
custody or an OS sandbox. Caller-held roots are mandatory; hashes do not prove
who approved a work order. No canonical tree is ever modified here.
"""
from __future__ import annotations
from pathlib import Path
import os
import stat
from .common import BOUNDARY, require, root, seal, check_seal, safe_relative, digest, read_bytes, exact_keys, path_is_alias

ROLES={'SPECIFICATION','ORACLE','DRIVER','RUNNER','CHECKER'}

def snapshot(folder:Path) -> dict:
    folder=Path(folder)
    require(folder.is_dir() and not path_is_alias(folder),'SNAPSHOT_DIRECTORY_REQUIRED')
    rows=[];seen=set()
    for directory,dirs,files in os.walk(folder,followlinks=False):
        for name in sorted(dirs+files):
            p=Path(directory)/name;require(not path_is_alias(p),'SNAPSHOT_SYMLINK_FORBIDDEN')
        for name in sorted(files):
            p=Path(directory)/name;relative=safe_relative(p.relative_to(folder).as_posix())
            folded=relative.casefold();require(folded not in seen,'SNAPSHOT_CASE_COLLISION');seen.add(folded)
            st=p.stat();require(stat.S_ISREG(st.st_mode) and st.st_nlink==1,'SNAPSHOT_FILE_ALIAS_FORBIDDEN')
            data=read_bytes(p)
            require(len(rows)<4096,'SNAPSHOT_FILE_LIMIT')
            rows.append({'path':relative,'sha256':digest(data),'bytes':len(data)})
    require(bool(rows),'SNAPSHOT_EMPTY')
    return seal({'schema':'miw.tree_snapshot.v1','files':sorted(rows,key=lambda r:r['path'])},'snapshot_root')

def freeze_basis(folder:Path,protected:dict,mutable:list[str]) -> dict:
    require(type(protected) is dict and set(protected)==ROLES,'VERIFICATION_BASIS_ROLES_REQUIRED')
    require(type(mutable) is list and mutable,'MUTABLE_PATHS_REQUIRED')
    for path in mutable:safe_relative(path)
    require(len(set(mutable))==len(mutable),'MUTABLE_PATH_DUPLICATE')
    basis=[]
    for role,paths in sorted(protected.items()):
        require(type(paths) is list and paths and len(set(paths))==len(paths),'PROTECTED_ROLE_PATHS_REQUIRED')
        for path in paths:basis.append({'role':role,'path':safe_relative(path)})
    pset={r['path'] for r in basis};require(not pset & set(mutable),'MUTABLE_PROTECTED_OVERLAP')
    snap=snapshot(folder);known={r['path'] for r in snap['files']}
    require(pset|set(mutable)<=known,'BASIS_PATH_MISSING')
    return seal({'schema':'miw.verification_basis.v1',**BOUNDARY,'snapshot':snap,'protected':basis,
        'mutable_paths':sorted(mutable),'approval_status':'NOT_AUTHENTICATED_LOCAL_CONSTRAINTS_ONLY',
        'effect_scope':'READ_ONLY_SNAPSHOT'},'basis_root')

def check_candidate(basis:dict,candidate:Path,expected_basis_root:str) -> dict:
    check_seal(basis,'basis_root');require(basis['basis_root']==expected_basis_root,'BASIS_EXTERNAL_PIN_MISMATCH')
    exact_keys(basis,{'schema','standing','authority_effect','snapshot','protected','mutable_paths','approval_status','effect_scope','basis_root'})
    require(basis['schema']=='miw.verification_basis.v1' and all(basis[k]==v for k,v in BOUNDARY.items()),'BASIS_BOUNDARY_INVALID')
    check_seal(basis['snapshot'],'snapshot_root')
    require(set(r['role'] for r in basis['protected'])==ROLES,'BASIS_ROLES_INCOMPLETE')
    old={r['path']:r for r in basis['snapshot']['files']};new_snapshot=snapshot(candidate)
    new={r['path']:r for r in new_snapshot['files']}
    protected={r['path'] for r in basis['protected']};mutable=set(basis['mutable_paths'])
    require(not protected & mutable and protected|mutable <= set(old),'BASIS_PATH_INVALID')
    changed=sorted(p for p in set(old)|set(new) if old.get(p)!=new.get(p))
    require(set(old)==set(new),'CANDIDATE_FILE_SET_CHANGED')
    require(not set(changed)&protected,'VERIFICATION_BASIS_CHANGED',detail=','.join(sorted(set(changed)&protected)))
    require(set(changed)<=mutable,'OUT_OF_SCOPE_CHANGE',detail=','.join(sorted(set(changed)-mutable)))
    return seal({'schema':'miw.candidate_scope_check.v1',**BOUNDARY,'basis_root':basis['basis_root'],
        'candidate_snapshot_root':new_snapshot['snapshot_root'],'changed_paths':changed,
        'status':'WITHIN_DECLARED_EDIT_SCOPE','correctness_status':'NOT_ESTABLISHED',
        'authority_status':'NOT_AUTHENTICATED','effect_scope':'READ_ONLY'},'scope_check_root')
