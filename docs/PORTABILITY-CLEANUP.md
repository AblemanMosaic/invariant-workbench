# Portability cleanup successor

This package is a separately identified successor to the accepted Zucchini-live archive
with SHA-256 `91935d6011f0bcec99fe74f0ee43c7e7d85e57317307e7d1d0de9cd6f924237b`.
That exact archive remains preserved as its own delivery. Its receipt, report and
checksum are carried under `history/zucchini-live-accepted/`; the 12.8 MiB ZIP is not
nested because it exceeds this package's intentional 8 MiB per-member read boundary.

## Corrections

1. `evidence/EXTERNAL-GATES.json` now records upstream Zucchini as
   `PASSED_PINNED_SCOPE` only for commit
   `e8595c9ae94e45c1e28a3effeb7555725c3ac741`, source root
   `e948fc1830887feeaff4f591d6064efdfea9ee93b9b7778c4c552e17ba224b1b`,
   the exact dependency envelope, and Linux/Ninja/Release. The stale predecessor
   register remains under `evidence/lineage/pre-portability-cleanup/`.
2. Host observations distinguish a local Python regression, a Windows local Python
   regression, native Windows GUI acceptance, and a Windows/Visual Studio Zucchini
   replay. Passing one lane no longer relabels the others.
3. The dossier generator writes governance fixture text as explicit UTF-8 bytes and
   orders manifest rows by canonical filename strings. This removes Windows newline
   translation and `Path`-flavor ordering from the dossier identity.

## Report semantics

The retained live run contains 35 report structures understood by the adapter. Nineteen
record successful discovery. Sixteen record discovery failure for deliberately invalid
upstream examples. “Supported report” means the structure was parsed under the bounded
profile; it does not mean every report describes successful application behavior.

## Claim ceiling

The cleanup does not convert tests into proof, extend acceptance to a later Zucchini
revision, validate a consuming MES implementation, close database or physical-inventory
assumptions, establish native Windows GUI/Visual Studio acceptance, or grant production
authority. It remains `INFORMATION_ONLY` with authority effect `NONE`.
