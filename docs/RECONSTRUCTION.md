# Turn 4 reconstruction and delivery repair

Status: experimental reconstructed successor. INFORMATION_ONLY; authority_effect NONE.
The original UCM version and all business example contracts remain unchanged.

## Identity and lineage

The delivered predecessor is exactly:

```
e3ddaa4bbace5761c2a02686f2eb0c5c683dd1338b2be5d29aeed21bd466c46b
```

Its archive has 380 members and 5,024,936 bytes. Its historical qualification is
387 distinct methods, including 64 Turn 4 methods. The advertised 391-method
72f8e68a6f86a0a223c8de9ee9836b52c38bc3bffe49163fddfe9db81f9eb29d archive
was not recovered. The standalone later receipt does not establish possession
of those bytes. It is retained in evidence/lineage only as a withdrawn mismatch.

This successor reconstructs the missing helper behavior, adds the separately
reported Windows correction, and requalifies a new exact source. It makes no
claim to recover the missing archive's original byte representation or hash.
The exact delivered predecessor is preserved outside this public-slim distribution.
Its declared identity remains above; the full custody successor retains the archive.
All predecessor evidence is historical and remains bound to its original source.

## Repair R1: replay output boundary

Both tools/replay_turn4.py and tools/reproduce_turn3_findings.py call the same
validate_replay_output check before creating output or launching subprocesses.
A new output may be outside the project or beneath its evidence/ directory.
Source-inventory destinations are refused, including evidence/../ paths.
Existing destinations and symlinked ancestors are refused before normalization.
The check returns a normalized path but creates nothing. It is not a sandbox
against a hostile administrator racing filesystem changes.

Four direct regression methods cover plain and traversal source-output paths
for each helper. Additional methods cover allowed paths, evidence-prefix
lookalikes, preexisting paths, and symlink aliases.

## Repair R2: Windows path-stat versus handle-stat

CPython 3.13.5 adds execute bits (0111) to Windows path-based stat results for
.exe, .bat, .cmd and .com filenames. Handle-based fstat does not apply that
filename adjustment. The old code compared their complete modes as if they
came from one API. The reported RUN_MIW.bat failure is consistent with that code.

The reconstructed read guard keeps full path-before/path-after equality and
full handle-open/handle-after equality, including mode. It also requires the
same device, inode, size and modification timestamp across both APIs. Only on
Windows, for those four suffixes, it permits the path mode to equal handle mode
with exactly the documented execute bits added. Other permission differences,
changed metadata and file-type changes still refuse. POSIX behavior is not
relaxed. The guard remains best-effort local consistency, not authenticated
custody or protection from metadata-restoring hostile writers.

Primary implementation reference, inspected during reconstruction:
https://raw.githubusercontent.com/python/cpython/v3.13.5/Modules/posixmodule.c
See update_st_mode_from_path, including its 0111 extension handling.

Metadata regressions use controlled observations on Linux. They are not an
actual Windows replay. A real file named RUN_MIW.bat is also read locally.
The reported predecessor Windows consolidated run was blocked; this repaired
successor still requires actual Windows acceptance. Native HWND acceptance is
another separate, still-open gate.

## Preserved guarantees and limits

Approved example source and contracts, selected UCM and Mosaic vendor files,
Foundry inputs and outputs, and original sun are unchanged. The engine identity
changes because common.py changes, so proof dossiers are regenerated and checked
against the new engine. No old record is silently promoted to the new subject.
The AST frontend remains trusted, not formally proved. Tests do not prove C++,
database concurrency, live Zucchini behavior, or physical stock.

## Exact-delivery check

The external reconstruction receipt is derived from the delivered ZIP bytes.
The final ZIP is byte-verified, extracted to a new directory, and subjected to
fresh full local replay without editing that ZIP afterward. The checksum is
computed again before delivery. This sequencing prevents the previous pairing
of a later report with an earlier archive. Byte identity still is not authority
or independent review.

Full fresh results belong in evidence/RECONSTRUCTION-COMPLETION.md and the
external receipt. Production admission, real signer custody and independent
review remain ungranted. No network model or production database is contacted.
