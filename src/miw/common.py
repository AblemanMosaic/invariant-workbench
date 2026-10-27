"""Strict data boundaries; local receipts are identities, not authority."""
from __future__ import annotations
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import stat
from typing import Any
from uclop.canonical import Refusal, require, exact_keys, root, strict_loads, canonical_bytes

BOUNDARY = {'standing': 'INFORMATION_ONLY', 'authority_effect': 'NONE'}
MAX_FILE = 8 * 1024 * 1024

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def seal(body: dict, field: str = 'record_root') -> dict:
    require(field not in body, 'ROOT_ALREADY_PRESENT')
    return {**body, field: root(body)}

def check_seal(record: Any, field: str = 'record_root') -> dict:
    require(type(record) is dict and field in record, 'SEALED_RECORD_REQUIRED')
    require(record[field] == root({k: v for k, v in record.items() if k != field}), 'RECORD_ROOT_MISMATCH')
    return record

# CPython's Windows path stat adds 0111 for executable filename extensions,
# while handle-based fstat does not. Never relax same-API before/after checks.
_WINDOWS_STAT_EXECUTE_COMPAT = os.name == 'nt'
_WINDOWS_EXECUTABLE_SUFFIXES = frozenset({'.bat', '.cmd', '.exe', '.com'})


def _assert_read_stability(path: Path, before, opened, after_fd, after_path) -> None:
    """Compare like observations strictly and allow only the known Windows quirk.

    This remains a best-effort local mutation check, not a security boundary
    against a hostile filesystem administrator restoring metadata or racing I/O.
    """
    def identity(s):
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_mode)

    require(all(stat.S_ISREG(s.st_mode) for s in (before, opened, after_fd, after_path)),
            'FILE_CHANGED_DURING_READ')
    require(identity(before) == identity(after_path) and
            identity(opened) == identity(after_fd), 'FILE_CHANGED_DURING_READ')
    require(identity(before)[:-1] == identity(opened)[:-1], 'FILE_CHANGED_DURING_READ')
    same_mode = before.st_mode == opened.st_mode
    windows_path_execute_bits = (
        _WINDOWS_STAT_EXECUTE_COMPAT and
        path.suffix.lower() in _WINDOWS_EXECUTABLE_SUFFIXES and
        before.st_mode == (opened.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    )
    require(same_mode or windows_path_execute_bits, 'FILE_CHANGED_DURING_READ')


def read_bytes(path: Path, limit: int = MAX_FILE) -> bytes:
    try:
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode), 'REGULAR_FILE_REQUIRED', detail=str(path))
        require(before.st_size <= limit, 'FILE_TOO_LARGE', detail=str(path))
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0))
        with os.fdopen(fd, 'rb') as stream:
            opened = os.fstat(stream.fileno())
            require(stat.S_ISREG(opened.st_mode), 'REGULAR_FILE_REQUIRED', detail=str(path))
            require((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), 'FILE_REPLACED_DURING_READ')
            data = stream.read(limit + 1)
            after_fd = os.fstat(stream.fileno())
        after_path = path.lstat()
        _assert_read_stability(path, before, opened, after_fd, after_path)
        require(len(data) <= limit and len(data) == before.st_size, 'FILE_TOO_LARGE_OR_INCOMPLETE')
        return data
    except OSError as error:
        raise Refusal('FILE_READ_FAILED', detail=str(path)) from error

def read_json(path: Path) -> Any:
    return strict_loads(read_bytes(path))

def path_is_alias(path: Path) -> bool:
    """Recognize POSIX symlinks and Windows directory junctions."""
    path=Path(path)
    isjunction=getattr(os.path,'isjunction',None)
    return path.is_symlink() or bool(isjunction is not None and isjunction(path))

def _check_output_ancestors(path: Path) -> None:
    # A local safety check, not protection from an administrator racing renames.
    for component in (path.parent, *path.parent.parents):
        require(not path_is_alias(component), 'OUTPUT_PARENT_SYMLINK_FORBIDDEN')
        if component.exists():
            require(component.is_dir(), 'OUTPUT_PARENT_NOT_DIRECTORY')

def write_output(path: Path, data: bytes, *, replace_existing: bool = False) -> None:
    """Create exclusively. Replacement is an explicit internal maintenance action.

    Reject symlink ancestors and aliased targets. The normal CLI never requests
    replacement. A hostile concurrent filesystem writer still needs OS isolation.
    """
    import tempfile
    require(type(data) is bytes and type(replace_existing) is bool, 'OUTPUT_ARGUMENT_INVALID')
    path = Path(path).absolute()
    _check_output_ancestors(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _check_output_ancestors(path)
    require(not path_is_alias(path), 'OUTPUT_SYMLINK_FORBIDDEN')
    previous = None
    if path.exists():
        previous = path.lstat()
        require(stat.S_ISREG(previous.st_mode) and previous.st_nlink == 1, 'OUTPUT_ALIASED_OR_NONREGULAR')
        require(replace_existing, 'OUTPUT_ALREADY_EXISTS')
    if previous is None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_BINARY', 0)
        try:
            fd = os.open(path, flags, 0o600)
        except FileExistsError as error:
            raise Refusal('OUTPUT_ALREADY_EXISTS') from error
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return
    fd, temporary = tempfile.mkstemp(prefix='.miw-output-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        _check_output_ancestors(path)
        current = path.lstat()
        def identity(st):
            return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_mode, st.st_nlink)
        require(identity(previous) == identity(current), 'OUTPUT_CHANGED_DURING_REPLACEMENT')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def write_json(path: Path, value: Any, *, replace_existing: bool = False) -> None:
    write_output(path, canonical_bytes(value) + b'\n', replace_existing=replace_existing)

def safe_relative(name: str) -> str:
    require(type(name) is str and 0 < len(name) <= 240, 'RELATIVE_PATH_INVALID')
    require('\\' not in name and ':' not in name and '\x00' not in name, 'RELATIVE_PATH_INVALID')
    p = PurePosixPath(name)
    require(not p.is_absolute() and all(x not in ('', '.', '..') for x in name.split('/')), 'RELATIVE_PATH_INVALID')
    require(not any(x.endswith((' ', '.')) for x in p.parts), 'RELATIVE_PATH_INVALID')
    return name

def identifier(value: Any) -> str:
    require(type(value) is str and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,47}', value) is not None,
            'IDENTIFIER_INVALID')
    return value

def implementation_identity() -> dict:
    """Bind active implementation bytes. Not an authenticity or freshness proof."""
    here = Path(__file__).resolve()
    base = here.parents[2]
    rows = []
    for folder in [base/'src', base/'vendor/ucm/uclop']:
        for file in sorted(folder.rglob('*.py')):
            rows.append({'path': file.relative_to(base).as_posix(), 'sha256': digest(read_bytes(file))})
    return seal({'schema': 'miw.engine_identity.v1', 'files': rows}, 'engine_root')


def validate_replay_output(project: Path, output: Path) -> Path:
    """Refuse source-inventory outputs before creating any directory or file.

    Evidence is excluded by source_inventory; every other descendant is source.
    Check lexical symlink ancestors before resolving '..' so aliases cannot be
    normalized away. This check is not an OS sandbox or a rename-race defense.
    """
    raw = Path(output).absolute()
    require(not raw.exists() and not any(path_is_alias(p) for p in (raw, *raw.parents)),
            'OUTPUT_DIRECTORY_ALREADY_EXISTS_OR_ALIASED')
    resolved = raw.resolve(strict=False)
    project = Path(project).resolve(strict=True)
    if resolved.is_relative_to(project):
        evidence = project / 'evidence'
        require(resolved != evidence and resolved.is_relative_to(evidence),
                'OUTPUT_INSIDE_SOURCE_INVENTORY')
    return resolved
