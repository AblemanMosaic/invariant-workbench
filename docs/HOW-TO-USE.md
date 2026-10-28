# Reconstruction entry point

This is a new, independently hashed reconstruction of the actual earlier Turn 4
archive. It is not the missing 72f8e68a archive. See RECONSTRUCTION.md.

```console
python -I -B ./tools/miw.py verify-dossier --directory ./evidence/qualification/demo
python -I -B ./tools/replay_turn4.py --out ./evidence/my-reconstruction-replay
```

Both replay helpers refuse outputs within the source inventory before mutation.
Use a fresh directory under ./evidence/ or outside the extracted project.
The Windows metadata compatibility fix has now passed the full regression on a real
Windows host, including junction-backed alias cases. Native HWND/UI acceptance remains
separate and open. Do not reuse an earlier proof dossier against changed engine bytes.

# Developer walkthrough | Turn 4 reconstructed candidate

## 1. Inspect the exact software

Keep the original ZIP and its externally supplied checksum. The standalone VERIFY.py
checks either the release archive or an ordinary Git clone against the closed byte
inventory without importing candidate application code. Clone verification ignores
only `.git/`; undeclared files and changed bytes refuse.

```console
python -I -B ./VERIFY.py --help
python -I -B ./VERIFY.py --directory .
python -I -B ./VERIFY.py ./Invariant_Workbench_v0.1.zip --sha256 <SHA256-FROM-SIDECAR>
python -I -B ./tools/miw.py --help
python -I -B ./tools/miw.py preflight
```

The core uses Python's standard library. The full regression needs `cryptography` for
the UCM fixture campaign and `jsonschema` for the realization-space schema court. The
recorded builder version is in the host evidence. There
is no implicit package installer. Optional PostgreSQL needs an explicitly installed
psycopg 3 and a dedicated, nonproduction server. Keep tool versions pinned when comparing
results. Native Windows execution remains an acceptance task on your machine.

## 2. Prove the small operation first

```console
python -I -B ./tools/miw.py prove --contract ./examples/assembly/contract.json --source ./examples/assembly/operation.py --out ./my-proof.json
python -I -B ./tools/miw.py verify-proof --contract ./examples/assembly/contract.json --source ./examples/assembly/operation.py --proof ./my-proof.json
python -I -B ./tools/miw.py test-feature --contract ./examples/assembly/contract.json --source ./examples/assembly/operation.py --feature ./examples/assembly/inventory.feature
```

The first two commands inspect and symbolically verify the supported source. The third
actually executes the closed scalar operation on the finite examples. A proof result
is not obtained by counting those examples. The new AST frontend is trusted, not a
formally proved compiler. Change the source and the old exact proof must not replay.

## 3. Follow the work order

```console
python -I -B ./tools/miw.py lifecycle-demo --out ./my-lifecycle.json
python -I -B ./tools/miw.py explore-lifecycle --out ./my-finite-graph.json
```

The lifecycle starts with one kit, reserves it, refuses a competing order and premature
completion, consumes it, adds a new recipe, and completes the original order even with
empty shelves. Repeating the same completion command returns its original receipt.
The exploration checks its stated finite model only. It is not a proof of all MES workflows.

## 4. Open the actual native viewer

```console
python -I -B ./tools/miw.py gui --directory ./evidence/qualification/demo
```

This uses the actual Mosaic Foundry/runtime on Windows, with the original sun asset.
On Linux use `headless-ui` or read `./evidence/qualification/demo/index.html` as a static
offline report. The HTML is not used as a native application wrapper. No UI action
mutates the source or calls an AI/DB endpoint. The six views are Overview, Rules and
Code, Proof and Tests, Work Orders, Proposals and Changes, and Integrations.

```console
python -I -B ./tools/recompile_ui.py --out ./my-foundry-recompile
```

Recompilation must reproduce both shipped generated files byte-for-byte. That is a
compiler replay check, not native Windows acceptance.

## 5. Use Zucchini without replacing its workflow

The generic adapter is already implemented; do not begin by writing another connector.
Read `./evidence/MES-DEVELOPER-START-HERE.md` and `./docs/ZUCCHINI-ADAPTER.md` for the exact
division between supplied plumbing and repository-specific inputs. The first real
handoff needs an immutable export/commit, one feature and its step definitions, the
build/dependency pins, intended report/test names, and a reviewed proposed mapping.

The read-only path accepts a report in the supported 2.2.0 profile and an independently
chosen JUnit file. Start with the included synthetic examples:

```console
python -I -B ./tools/miw.py import-zucchini --report ./fixtures/zucchini/rules.synthetic.json --out ./my-import.json
python -I -B ./tools/miw.py bind-junit --report ./fixtures/zucchini/rules.synthetic.json --junit ./fixtures/zucchini/results.synthetic.xml --out ./my-binding.json
python -I -B ./tools/miw.py link-junit --report ./fixtures/zucchini/rules.synthetic.json --junit ./fixtures/zucchini/results.synthetic.xml --binding ./my-binding.json
```

The binding records a caller assertion, not authenticated same-build provenance.
Skipped/missing tests are not passes; a failing scenario is not automatically a
counterexample to every requirement it mentions.

For a real upstream source tree, first obtain a reviewed immutable export and its
commit/provenance by a trusted channel. Use an exported tree without `.git` internals,
in an externally isolated environment when the code is not trusted. The runner will
execute CMake and CTest. The bundled evidence records a successful run against exact
upstream commit `e8595c9ae94e45c1e28a3effeb7555725c3ac741`.

```console
python -I -B ./tools/miw.py snapshot --directory ./upstream-source --out ./upstream-pin.json
python -I -B ./tools/miw.py run-zucchini --source-directory ./upstream-source --expected-source-root ROOT_FROM_UPSTREAM_PIN_JSON --upstream-commit EXACT_40_CHARACTER_COMMIT --generator Ninja --build-config Release --cmake-define ZUCCHINI_NLOHMANN_JSON_SOURCE_DIR=/pinned/nlohmann-json --cmake-define ZUCCHINI_NLOHMANN_JSON_SCHEMA_VALIDATOR_SOURCE_DIR=/pinned/json-schema-validator --cmake-define ZUCCHINI_LIBFYAML_SOURCE_DIR=/pinned/libfyaml --cmake-define ZUCCHINI_CUCUMBER_GHERKIN_SOURCE_DIR=/pinned/gherkin --cmake-define ZUCCHINI_GOOGLETEST_SOURCE_DIR=/pinned/googletest --cmake-define ZUCCHINI_TPP_BIN_DIR=/pinned/tpp/bin --cmake-define ZUCCHINI_FETCH_TPP=OFF --accept-report PATH_RELATIVE_TO_BUILD/rules.json --allow-trusted-build --out ./my-zucchini-run
```

Replace every placeholder with an inspected value. The source root is an intentional
caller-held byte pin; the commit is separately supplied provenance, not inferred approval.
Dependencies must already be available. Automatic dependency fetching is disabled. The
runner records actual commands, return codes, report imports and incomplete execution.
Unknown report semantics remain refused. For the exact accepted dependency identities,
command shape, raw report and CTest output, read `evidence/zucchini-live-acceptance/`.

## 6. Review an optional model proposal

`./evidence/integration/proposals/` contains a complete offline example. REQUEST.json
is bound to the exact defective source, contract and checking-basis root. RESPONSE.json
is explicitly a builder-authored scenario fixture, not a claim that AI found it.
REVIEW.json demonstrates requirement-specific failure attribution and no spec approval.

For your project, create a checking-basis policy with nonempty SPECIFICATION, ORACLE,
DRIVER, RUNNER and CHECKER path lists and a separate `mutable` list. These paths must
refer to actual files under the chosen directory. Then:

```console
python -I -B ./tools/miw.py freeze-basis --directory ./your-project --policy ./your-policy.json --out ./your-basis.json
python -I -B ./tools/miw.py proposal-request --contract ./your-project/contract.json --source ./your-project/operation.py --target REQ_A_ACCOUNTING --basis-root ROOT_FROM_YOUR_BASIS_JSON --out ./your-request.json
```

A response contains only `kind`, `request_root`, and native scalar `feature` text.
It cannot include code changes or approval. Review against current inputs:

```console
python -I -B ./tools/miw.py review-proposal --contract ./your-project/contract.json --source ./your-project/operation.py --request ./your-request.json --response ./your-response.json --expected-request-root ROOT_FROM_YOUR_REQUEST_JSON --basis-root ROOT_FROM_YOUR_BASIS_JSON --out ./your-review.json
```

The optional Ollama client is off by default and contacts only an explicitly enabled
loopback endpoint. It sends the request's code and requirements to that local service.
Use an already installed offline local model and verify the service is not relaying
elsewhere; loopback alone is not proof of offline inference. No model is downloaded.

```console
python -I -B ./tools/miw.py ollama-propose --request ./your-request.json --model YOUR_INSTALLED_LOCAL_MODEL --allow-local-model --out ./your-response.json
```

Feed the saved text through `review-proposal`; the transport never marks it approved.
The actual model lane was NOT_RUN by this builder.

## 7. Exercise real UCM interfaces with fixture identities

```console
python -I -B ./tools/miw.py ucm-fixture --out ./my-custody-campaign
python -I -B ./tools/ucm_custody_tests.py --out ./my-inherited-custody-tests
```

These invoke unchanged native UCM interfaces and real signature verification, but the
identities are reproducible test fixtures. They do not authenticate you as Governor.
The campaign inspects source, prepares a fresh implementation candidate and runs three
trusted tests bound to that candidate receipt. It retains the original source and
refuses a stale external head. Production custody and OS isolation remain external.

## 8. PostgreSQL acceptance, explicitly opt-in

Use a dedicated disposable database, never an existing business database. Review
`./sql/reference.sql` and `./docs/POSTGRESQL-BOUNDARY.md`. The harness creates a new
random tenant, performs real writes and leaves its rows for inspection. It does not
silently reset or drop an existing tenant. Credentials are read from an environment
variable and are not included in the evidence.

PowerShell, after setting a suitable local-only test connection string:

```powershell
$env:MIW_TEST_PG_DSN = 'host=127.0.0.1 dbname=miw_test user=miw_test'
python -I -B ./tools/miw.py postgres-live --allow-disposable-database --out ./my-pg-run
```

No DSN means NOT_RUN and a nonzero command status. Missing psycopg means refusal.
The live campaign tests competing last-kit reservations, duplicate IDs, mismatched
payload reuse, premature completion, rollback, attributed consumption, simulated lost
commit acknowledgement around a real COMMIT, reconciliation and final accounting.
It is a test campaign, not a concurrent-execution theorem. It was NOT_RUN here.

## 9. Requalify a change and replay the batch

```console
python -I -B ./tools/miw.py integration-demo --out ./my-integration
python -I -B ./tools/qualify.py --out ./my-qualification
```

The maintenance example changes A consumption from two to three, invalidates the old
proof and examples, and verifies the new operation before running its updated examples.
Machine timings are observations, not claims of lower human effort.

Output directories must be fresh. The standalone verifier checks the distributed
archive, not any later directory that you have edited. Retain old evidence as history
and generate a new exact subject for changed code.

A separate actual-native smoke procedure switches all six views through the Win32
message loop and records its scope. On Linux it records NOT_RUN and exits nonzero.

```console
python -I -B ./tools/ui_smoke.py --directory ./evidence/qualification/demo --out ./my-native-witness.json
```


## 10. Review the repair, without confusing it with independent review

The public-slim package does not embed the exact Turn 3 predecessor. Its identity and
before-repair observations remain in `./evidence/review/`. The review report
distinguishes seven reproduced defects, regression closures, trusted components and
missing external legs.

```console
python -I -B ./tools/reproduce_turn3_findings.py --allow-reviewed-subject --out ./my-prior-findings
```

This optional command works only after a separately obtained archive with the declared
Turn 3 hash is placed at `./history/turn3/FROZEN-CANDIDATE.zip`. It explicitly executes
that known frozen predecessor in a disposable output tree. It is not a sandbox or an
independent review. CMake and CTest are required for the zero-test finding. The tool
never executes an arbitrary supplied archive.

Normal JSON outputs are created exclusively. Explicit replacement is reserved for
internal manifest maintenance and mutation tests. Linked output paths are refused.
The CLI still permits an existing byte-identical output without rewriting it.

The new dossier retains mutant execution snapshots and raw import inputs. Verification
checks their internal consistency and exact bindings, but does not rerun those
recorded executions or authenticate their producer. Regenerate a demo for fresh runs.

## 10. Replay the consolidated Turn 4 batch

```console
python -I -B ./tools/replay_turn4.py --out ./evidence/my-turn4-replay
```

This runs the local regression/proof qualification, unchanged UCM custody tests,
fixture integration, Foundry recompilation and headless viewer checks. Use a new
output directory. Add `--include-local-cpp` only to compile and execute the included
builder-authored C++ probe with your installed compiler. Neither form downloads
packages, connects a model or database, or obtains an independent review.

To reproduce predecessor defects deliberately, first obtain and verify the separately
preserved archive, then use a disposable local workspace after inspecting the helper:

```console
python -I -B ./tools/reproduce_turn3_findings.py --allow-reviewed-subject --out ./my-predecessor-challenges
```

That command checks the frozen Turn 3 archive pin, extracts it, and executes the
recorded benign challenges. The public-slim package intentionally does not supply the
archive itself. It requires CMake/CTest for the empty-build observation. It is not a
sandbox. Seven observations explain why this repair successor exists; reproducing a
bug is distinct from approving either the old or new candidate.
