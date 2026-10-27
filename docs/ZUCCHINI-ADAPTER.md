# Zucchini integration contract

## Division of work: the adapter is already supplied

The consuming MES developer is not being asked to write a generic MIW connector. MIW owns report parsing,
strict validation, report/JUnit custody, CMake/CTest invocation, scenario linkage,
proposed obligation bindings, and acceptance receipts. It also supplies the
disposable-copy wrapper for fixture-mutating suites and a separately gated PostgreSQL
reference campaign.

The consuming repository supplies only facts MIW cannot responsibly invent:

| Supplied by the repository owner | Why it cannot be guessed |
| --- | --- |
| Immutable source export, source root, and separately obtained commit | Identifies the exact code and provenance under review |
| Generator, build configuration, and pinned dependency directories | Defines the executable build lane without hidden fetching |
| Intended acceptance report path and matching test names | Distinguishes the business example from diagnostic fixtures |
| One real feature and its step definitions | Establishes what Zucchini actually executes |
| Proposed requirement correspondence and reviewer | Similar words do not establish semantic equivalence |
| Database schema/units, transaction boundary, roles, and complete writer inventory | Atomicity cannot protect a path that bypasses it |

The initial integration should therefore be configuration and review, not new adapter
code. Extend the adapter only if the real output uses an unsupported schema or execution
dialect; preserve the raw rejected input as the regression fixture before changing it.

## Read-only report support

The existing profile accepts the previously inspected 2.2.0 report shape. It preserves
source/discovery identities, semantic requirement associations and discovery outcomes.
JUnit is separately associated through an explicit byte-bound caller assertion. That
association is not independent authentication. A skipped or missing execution cannot
become a pass. A failed scenario alone does not establish which named obligation failed.

The files under `fixtures/zucchini/` are synthetic. Exact raw outputs from the pinned
live build are separately retained under `evidence/zucchini-live-acceptance/`. Existing
tests are retained and rerun. No report field or schema version is silently upgraded.

## New opt-in execution adapter

`run-zucchini` requires an exported source directory, its caller-held snapshot root,
the exact 40-character upstream commit, a new outside output directory and
`--allow-trusted-build`. It checks the source before and after execution, invokes CMake
with ZUCCHINI_FETCH_DEPENDENCIES=OFF and tests enabled, builds and invokes CTest with
JUnit output. It then imports discovered candidate reports under the same strict support
profile. `--accept-report` identifies which report or reports constitute acceptance;
other valid diagnostic reports remain observations. Logs, return codes, missing targets,
and refused imports remain visible. An incomplete build does not manufacture evidence.

This is not an OS sandbox. A CMake project can execute arbitrary code. Review and pin
upstream source/dependencies and use an external sandbox before admitting untrusted
repositories. No package installation or dependency download is performed by the runner.
A source snapshot is a byte identity, not a Git-origin attestation.

## Acceptance repair

The bounded JUnit profile recognizes CTest run/fail/notrun markers and GoogleTest
completed/suppressed/skipped markers. Explicit unknown states, contradictory markers,
incorrect present suite counters, and misplaced/unattributed results refuse. A marker
that says failed can no longer default to PASSED merely because a failure child is
absent. Generic JUnit dialect compatibility is not claimed.

The build adapter requests `ctest --no-tests=error` and requires supported report data,
matched executions and consistent successful outcomes before returning successful
acceptance. A successful empty CMake build is not a successful Zucchini integration.
The no-fetch CMake flag requests behavior from trusted build scripts; it is not an
OS-enforced network boundary. The recorded live campaign therefore added Bubblewrap
network and mount isolation outside the runner.

Real Zucchini emits parameterized GoogleTest names in the form
`Fixture.Test  # GetParam() = Test`. The linker now recognizes that exact bounded form,
while refusing ambiguous bare/prefixed matches. It also accepts Zucchini's numbered
duplicate scenario display names only when the suffix is the generated ` #N` form.

## Pinned live result

The final campaign used upstream commit
`e8595c9ae94e45c1e28a3effeb7555725c3ac741`, Git tree
`4b835316082df150d7683fa983e8c6d750e5d39c`, and exported source root
`e948fc1830887feeaff4f591d6064efdfea9ee93b9b7778c4c552e17ba224b1b`.
Its exact dependency closure and CMake 3.31.8 were admitted through a read-only envelope.
The Release/Ninja build passed, all 267 CTest tests passed, and 35 report structures
were supported with zero refusals. Nineteen record successful discovery; sixteen are
diagnostic discovery failures from deliberately invalid examples. All four scenarios
in the named Shop acceptance report linked to passed CTest executions. The source root
was identical before and after the run.

Raw evidence and hashes are in `evidence/zucchini-live-acceptance/`. This establishes
compatibility only for that pinned Linux lane. It is not proof of Zucchini, proof of the
Shop rules, acceptance of a consuming MES application, or compatibility with later commits.
Native Windows/Visual Studio replay and independent review remain open.

## Running a pinned project

First snapshot the exported source. Then supply the exact Git commit as separately
obtained provenance, an explicit generator/configuration, local dependency paths through
the allowlisted `--cmake-define` options, and at least one `--accept-report` path. For
the accepted upstream revision, TPP v0.18.0 must already be built and its expected
`.zucchini-tpp-v0.18.0.stamp` retained beside the tool directory when fetch is disabled.

Run the command inside an OS sandbox if any admitted source or build script is untrusted.
`tools/zucchini_acceptance_wrapper.py` can create and verify a disposable writable source
copy for suites that intentionally edit fixtures. It supplies custody, not an OS sandbox.

## Ready-made integration sequence

Use a fresh output for every step. The synthetic smoke confirms command shape without
contacting a build tool:

```console
python -I -B ./tools/miw.py import-zucchini --report ./fixtures/zucchini/rules.synthetic.json --out ./evidence/smoke-import.json
python -I -B ./tools/miw.py bind-junit --report ./fixtures/zucchini/rules.synthetic.json --junit ./fixtures/zucchini/results.synthetic.xml --out ./evidence/smoke-binding.json
python -I -B ./tools/miw.py link-junit --report ./fixtures/zucchini/rules.synthetic.json --junit ./fixtures/zucchini/results.synthetic.xml --binding ./evidence/smoke-binding.json --out ./evidence/smoke-link.json
```

For the real checkout:

1. `snapshot` the reviewed source export and retain its `source_root` externally.
2. Run `run-zucchini` with the exact commit, generator/configuration, allowlisted local
   dependency paths, at least one `--accept-report`, explicit `--allow-trusted-build`,
   and an external OS sandbox appropriate to the repository.
3. Preserve the adapter output directory unchanged. It contains command lines, return
   codes, report imports, linked tests, source-before/source-after identity, and the
   terminal acceptance status.
4. Copy `examples/assembly/workbench.bindings.json`; replace only the proposed tags and
   rationales after reading the real feature and step definitions.
5. Run `workbench-open`, `workbench-explain`, `workbench-select`, and
   `workbench-lower`. A Zucchini review never becomes a source proof by binding.
6. Model one small rule in the restricted proof lane only when the correspondence is
   reviewable. Keep the C++ execution and mathematical twin as separate artifacts.
7. Before database claims, map the supplied reference adapter to a disposable schema
   and enumerate every production writer. Run `postgres-live` only on the disposable
   test service; keep physical-stock correspondence as a measured assumption.

### Minimum acceptance matrix

| Lane | Required positive observation | Required negative observation | Terminal boundary |
| --- | --- | --- | --- |
| Import | Intended 2.2.0 report is supported | Unsupported/contradictory report refuses | Report interpretation only |
| Execution link | Every named scenario has one passed, non-skipped match | Missing, skipped, ambiguous, or failed match cannot pass | Exact report/JUnit binding, not authentication |
| Rule correspondence | Reviewer accepts the proposed mapping | Similar-name auto-binding is absent | Proposal, not proof |
| Mathematical twin | All native obligations check for the exact modeled operation | Defective variants leave residual obligations | Restricted model only |
| Database | Disposable campaign observes atomic success/refusal, retry, idempotency, and reconciliation | Bypass, changed-payload reuse, rollback, and lost-ack paths are exercised | Named schema/roles/configuration only |
| Requalification | Final source root is unchanged during the zero-skip gate | Changed source or assumption invalidates old evidence | Builder-authored qualification, not certification |

The complete MES-developer-facing handoff, including the exact information to send and the
claims available after each lane, is `evidence/MES-DEVELOPER-START-HERE.md`.
