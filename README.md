# Invariant Workbench v0.1 | successor engineering workspace

**Experimental, local-first software. INFORMATION_ONLY. Authority effect: NONE.**
No UCM release version has changed. This reconstructs repairs on the actually delivered
Turn 4 archive (`e3ddaa4b...`), not on the unavailable advertised `72f8e68a...` archive.
It has a new archive identity and is not byte-for-byte recovery. The accepted
Zucchini-live predecessor (`91935d60...`) remains a separately preserved delivery.
This public-slim package retains the current pinned-live receipt and useful raw results
under `evidence/zucchini-live-acceptance/`, but deliberately omits embedded predecessor
archives and redundant dependency-envelope inventories. Read `PUBLIC-PACKAGE.md`,
`docs/PORTABILITY-CLEANUP.md` and `evidence/RECONSTRUCTION-COMPLETION.md` first.

## What this package does

It connects readable business requirements, a restricted executable operation,
checked UCM arithmetic proofs, scenario execution, and explicitly bounded evidence.
The shared engine supports a native scalar workflow and read-only Zucchini reports.
The carried Turn 3 functionality includes a work-order model, a PostgreSQL reference adapter, optional proposal
workflow, actual UCM fixture custody, an actual Mosaic Foundry viewer, and change
requalification. Each result retains its own scope.

This successor adds an interactive, evidence-class-preserving Obligation Ledger and
Obligation Board. `Mosaic` now names the pinned UI realization layer rather than the
product identity. It also adds a bounded constitutional control surface: CTR courts,
an agent-readable capability/effect registry, independent operation commitments,
ESA/EVS/COP/SRSA posture, read-only diagnostics, and a semantic HeadlessRunner.
The sealed self-contract and generated `explain` surface make its own bounded
guarantees, nonclaims, trusted assumptions, enforcement paths, courts, evidence
schemas, and invalidation rules directly queryable without claiming recursive proof.
See `docs/INVARIANT-WORKBENCH-WORK-PROGRAM.md` and
`docs/CONSTITUTIONAL-CONTROL-SURFACE.md`. Start with `docs/SELF-CONTRACT.md`.

| Area | Implemented and exercised here | Boundary still open |
|---|---|---|
| Scalar proof | Native UCM certificates for assembly and capacity allocation; checked before example execution | New AST frontend is trusted, not a proved compiler; not arbitrary Python or C++ |
| Work orders | Receive, reserve, consume, complete, cancel unconsumed reservations, add immutable recipe revisions | Pure reference model, not an unbounded lifecycle proof |
| PostgreSQL | Serializable tenant-row adapter, durable operation IDs, retries and reconciliation; fault-driver tests | No live server or psycopg on builder host; live acceptance NOT_RUN |
| Zucchini | Exact upstream commit `e8595c9a...` built offline; all 267 CTest tests passed; 35 report structures supported (19 successful discovery, 16 expected diagnostics); four named Shop executions linked | Exact pinned Linux/Ninja/Release lane only; not arbitrary revisions, a consuming MES codebase, or formal proof |
| Proposals | Contract/source/basis-pinned requests; strict scenario-only response checks; exact failure attribution | Offline fixture responses only; actual AI model NOT_RUN |
| UCM custody | Actual unchanged manager/worker execution, Ed25519 fixture receipts, stale-head refusal, inherited tests | Fixture identities and process-local anchor do not seat a real Governor |
| UI | Actual Mosaic Foundry outputs, pinned HEADLESS/WIN32 runtime, and a passed Windows Python replay | Native HWND acceptance remains NOT_RUN |
| Control plane | Closed operation registry, CTR courts, three observability levels, compiled plans, local posture and diagnostics | Consumer-owned local candidate; native UGK runtime/admission and external effect acceptance remain open |
| Maintenance | Recipe coefficient change invalidates old evidence; revised operation is requalified | Builder-scripted change, not a measured human productivity study |

A compiled **builder-authored C++ scalar probe** is included separately. It is a
finite differential experiment, not an upstream Zucchini run or a C++ proof.

## Turn 4 repair and standing

Seven concrete builder findings were reproduced against the frozen predecessor.
The repair tightens imported outcome parsing, database connection/commit handling,
record consistency, output custody, proposal validation and external test acceptance.
The approved business operations and both vendored substrates remain unchanged.

**Engineering candidate only.** A bounded external artifact review reproduced the local
tests and report linkage but did not rebuild upstream Zucchini or perform production
admission. This is not completion of inherited UCM review. The proposed Governor
disposition remains pending.
The seven principal repairs are inherited. This successor adds the missing
replay-output guards, a narrow Windows metadata compatibility correction, and the
source-pinned upstream Zucchini acceptance recorded under
`evidence/zucchini-live-acceptance/`. This cleanup additionally scopes the current gate
register, separates three Windows execution lanes, and removes host-dependent dossier
bytes. See `docs/PORTABILITY-CLEANUP.md` for the exact delta.

## Start here

Extract to a short local path, for example `C:\MIW`. Python 3.12+ is intended;
actual acceptance in this package identifies the specific interpreter tested.
No auto-install, auto-upgrade, telemetry, hosted account or AI call occurs at startup.

Verify a Git clone before running it:

```console
python -I -B ./VERIFY.py --directory .
```

```console
python -I -B ./tools/miw.py verify-dossier --directory ./evidence/qualification/demo
python -I -B ./tools/miw.py lifecycle-demo
python -I -B ./tools/miw.py explore-lifecycle
python -I -B ./tools/miw.py preflight
python -I -B ./tools/miw.py validate-realization-space
python -I -B ./tools/miw.py workbench-open --directory ./evidence/qualification/demo --out ./evidence/my-workspace.json
python -I -B ./tools/miw.py capability-surface --out ./evidence/my-capabilities.json
python -I -B ./tools/miw.py self-contract-check --out ./evidence/my-self-contract-check.json
python -I -B ./tools/miw.py explain --out ./evidence/my-self-contract-index.json
python -I -B ./tools/miw.py explain --id G-FAIL-CLOSED --out ./evidence/my-fail-closed-explanation.json
python -I -B ./tools/miw.py constitutional-test --directory ./evidence/qualification/demo --bindings ./examples/assembly/workbench.bindings.json --out ./evidence/my-ctr.json
```

On Windows, open the real native viewer:

```console
python -I -B ./tools/miw.py gui --directory ./evidence/qualification/demo
```

`./RUN_MIW.bat` invokes the same path. On other systems the GUI command refuses
with WIN32_HOST_REQUIRED. It does not silently substitute Tk or a browser.
The old Tk source remains a clearly labeled legacy reference, not the default UI.
The static HTML dossier is a separate offline report, not the native application.

```console
python -I -B ./tools/miw.py headless-ui
python -I -B ./tools/recompile_ui.py --out ./evidence/my-ui-recompile
```

Use a new output directory for each replay. Core proof, BDD, model and Foundry
headless use the standard library. Fixture custody needs `cryptography`, and the
realization-space schema court needs `jsonschema`.
Full self-test includes that custody integration and will not silently skip it.
The optional live PostgreSQL lane separately needs psycopg 3 and a disposable server.
See `./docs/HOW-TO-USE.md` before enabling any effectful command.

## Full local replay

```console
python -I -B ./tools/qualify.py --out ./evidence/my-qualification
python -I -B ./tools/ucm_custody_tests.py --out ./evidence/my-custody-tests
python -I -B ./tools/miw.py integration-demo --out ./evidence/my-integration
```

One-command replay (new output folder required):

```console
python -I -B ./tools/replay_turn4.py --out ./evidence/my-reconstruction-replay
```

The output records, not this README, hold measured final test counts. This public-slim
distribution carries the exact identities of the historical subjects but not their
embedded ZIP bytes. Place a separately obtained, hash-matching Turn 3 archive at
`history/turn3/FROZEN-CANDIDATE.zip` only when deliberately running the optional
historical reproduction helper. Old proof bindings are not silently promoted to
changed engine bytes. Current runnable evidence is in `evidence/qualification/`,
`evidence/integration/`, and `evidence/public-slim-qualification/`.

## Main source

- `src/miw/proofs.py`, `restricted.py`, `bdd.py`: scalar source/contract evidence.
- `src/miw/lifecycle.py`, `postgres.py`, `live_postgres.py`: model and effect boundary.
- `src/miw/proposals.py`, `changes.py`: proposed scenarios and change explanations.
- `src/miw/custody_bridge.py`: actual native UCM fixture campaign.
- `src/miw/foundry_view.py`, `foundry/`, `vendor/mosaic/`: actual Mosaic UI.
- `src/miw/constitutional.py`, `src/miw/headless_runner.py`, `constitutional/`: bounded control plane and courts.
- `src/miw/external_build.py`: explicitly admitted, pinned source build adapter.
- `docs/REVIEW-HANDOFF.md`: Remaining independently executable review and acceptance matrix.

**No result in this package proves physical inventory, all external writers,
production authorization, or correctness of an unspecified application.**

## License

Invariant Workbench is licensed under the Apache License, Version 2.0. See `LICENSE`
and `NOTICE`. Bundled third-party components retain their applicable licenses and
notices; see `THIRD-PARTY-NOTICES.md` and the relevant vendored directories.
