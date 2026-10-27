# Pinned live Zucchini acceptance

Status: **PASSED for the exact pinned lane described below.**

This campaign executed the real upstream AnarchoSystems/Zucchini source at commit
`e8595c9ae94e45c1e28a3effeb7555725c3ac741` (Git tree
`4b835316082df150d7683fa983e8c6d750e5d39c`). The exported source snapshot root was
`e948fc1830887feeaff4f591d6064efdfea9ee93b9b7778c4c552e17ba224b1b`.

## Result

- CMake configure: passed.
- Ninja Release build: passed.
- Full upstream CTest suite: 267 passed, 0 failed.
- Generated Zucchini report structures supported: 35.
- Successful-discovery reports: 19.
- Diagnostic discovery-failure reports from deliberately invalid examples: 16.
- Report refusals: 0.
- Named acceptance report: `Examples/Good/BusinessRules/zucchini-reports/Shop/Release/rules.json`.
- Named report/JUnit matches: 4, all `PASSED`.
- Source snapshot after build and tests: unchanged.
- Runner exit code: 0.

The four linked executions cover buying two items, insufficient funds changing
nothing, sold-out purchase changing nothing, and refund restoration. Their raw
Zucchini report, CTest JUnit, and exact MIW linkage are retained here.

“Supported” means the bounded importer understood the report structure. It does not
turn a diagnostic report's failed discovery into successful application behavior.

## Custody and isolation

The source, CMake 3.31.8, CPM, direct dependencies, and prebuilt TPP tools were
assembled into a read-only manifest-verified envelope. Bubblewrap supplied PID, IPC,
UTS, cgroup, user, and network isolation; `/mnt/c` was not mounted. A verified copy of
the source was made writable inside the disposable work directory because four upstream
tests intentionally edit and restore fixtures. MIW checked the source root before and
after execution. The terminal receipt root is
`3c080c45b4e043d3dbbed68cdf6fbb632666eba48909fa5247bb2856c06dc7df`;
the MIW summary record root is
`7cf94d931b4b24f3f56a5eeafc42a66a764bd5fc92ce53033d7ff11c5f082c2c`.

Zucchini's offline TPP path still names `.zucchini-tpp-v0.18.0.stamp` as a build
dependency even when `ZUCCHINI_FETCH_TPP=OFF`. The campaign supplied that stamp beside
exact locally built TPP v0.18.0 binaries. This is an upstream offline-build integration
quirk, not evidence that a network fetch occurred.

## What this establishes

The MIW adapter can configure, build, test, discover real 2.2.0 reports, parse their
duplicate-outline naming, and associate real CTest/GoogleTest parameterized names for
this exact upstream revision and dependency closure.

It does not prove the scenarios, authenticate an upstream release, establish physical
inventory truth, accept a consuming application, or generalize to later revisions. It is
builder-produced `INFORMATION_ONLY` evidence with authority effect `NONE`, not an
independent review. Native Windows/Visual Studio replay remains open.

## Public-slim evidence map

- `RECEIPT.json`: compact identities, results, and file hashes.
- `ZUCCHINI-SNAPSHOT.json`: every exported source file and snapshot root.
- `RECEIPT.json`: compact identities, results, and hashes for both retained and
  externally preserved raw records.
- `TERMINAL.json`: final command custody receipt.
- `SUMMARY.json`: complete MIW import and JUnit-link result.
- `ctest.xml`, `test.log`: raw full-suite result.
- `configure.log`, `build.log`: raw configure and compilation output.
- `shop-report/`: exact generated report/dashboard files.
- `tpp-prep/`: retained terminal and summary.

The full custody successor additionally retains the 6.9 MB final build-envelope
manifest and the 5.1 MB TPP-preparation envelope manifest. The public-slim package
omits those repetitive file inventories and makes no claim that their member rows can
be replayed from this subset. `PUBLIC-SLIM-HASH-AUDIT.json` records that 14 of the 15
inherited receipt declarations match the retained/full-successor bytes; the final
build-envelope declaration is stale by 21 bytes and is preserved as a disclosed
historical mismatch rather than silently treated as the current file identity.
