# MES developer: what the Invariant Workbench gives you

This package is meant to sit beside Zucchini, not replace it. The practical workflow
is: **run your normal Zucchini examples, import their exact outputs, bind them to an
explicit business obligation, and separately attach proof or runtime evidence where
that stronger evidence actually exists.**

For the inventory rule, MIW supplies a proved small mathematical twin of one operation:
consume the required components and record the finished good, or refuse without
changing inventory. The proof is produced before example execution for every valid
input accepted by the restricted model. Five examples and seven deliberately defective
variants remain separate evidence.

That does not prove your C++ application, database, or physical warehouse. It gives
you a precise target and a custody system for showing which implementation, scenario,
execution, proof, and assumption support each claim without silently upgrading one
kind of evidence into another.

## You do not need to build the generic adapters

The package already provides:

- strict Zucchini 2.2.0 report import with cross-reference and coverage checks;
- explicit byte-bound JUnit association and scenario-to-test linkage;
- a pinned CMake/CTest runner with no-fetch configuration, zero-test refusal,
  source-before/source-after checks, and retained logs;
- a disposable-copy wrapper for suites that intentionally edit their fixtures;
- proposed MIW/Zucchini requirement bindings and an obligation-board workflow;
- the restricted proof, BDD, counterexample, and dossier-replay lanes;
- a PostgreSQL reference adapter with SERIALIZABLE transactions, durable operation
  IDs, retries, lost-acknowledgement reconciliation, and a live disposable-DB harness;
- the sealed `self-contract-check` and `explain` surfaces describing what MIW itself
  claims, assumes, refuses, and must requalify after change.

Your repository-specific contribution is deliberately smaller:

1. provide an immutable source export and its separately obtained Git commit;
2. identify the build generator, already pinned local dependency directories, and
   the report path that represents the intended acceptance example;
3. provide one real feature plus its step definitions and test name(s);
4. review the proposed semantic correspondence—MIW will not infer equivalence from
   similar names;
5. for database acceptance, identify your schema/columns/units, every write path,
   transaction boundary, service role, retry policy, and a disposable test DSN;
6. decide which humans may approve a mapping, waive a gap, or admit a release.

If an uncontrolled writer exists, a report is not from the same build, or the database
does not correspond to the mathematical state, MIW keeps that as an open assumption or
refusal. That is the point, not an integration failure.

## First ten minutes: inspect the proof and MIW's own contract

Use fresh output names.

```console
python -I -B ./tools/miw.py verify-dossier --directory ./evidence/invariant-workbench-demo-v8
python -I -B ./tools/miw.py self-contract-check --out ./evidence/my-self-contract-check.json
python -I -B ./tools/miw.py explain --id G-EVIDENCE-CLASS-SEPARATION
python -I -B ./tools/miw.py explain --id NC-PHYSICAL-INVENTORY
python -I -B ./tools/miw.py prove --contract ./examples/assembly/contract.json --source ./examples/assembly/operation.py --out ./evidence/my-proof.json
python -I -B ./tools/miw.py test-feature --contract ./examples/assembly/contract.json --source ./examples/assembly/operation.py --feature ./examples/assembly/inventory.feature
```

The example accepts exactly `q > 0`, `a >= 2q`, and `b >= q` for nonnegative
starting state. Success consumes `2q` A and `q` B and adds `q` finished units;
refusal preserves state. The AST-to-contract frontend, Python/runtime/OS, proof checker,
and approved requirement meaning remain explicit trusted assumptions.

## Lowest-friction integration with your checkout

No C++ modification is required for the first pass if Zucchini already emits a report
and CTest/JUnit output.

1. Make a reviewed export of the exact checkout and snapshot it:

```console
python -I -B ./tools/miw.py snapshot --directory ./your-zucchini-project --out ./evidence/your-source-pin.json
```

2. In an OS sandbox, run the bundled pinned adapter. Copy `source_root` from the
snapshot receipt and replace every placeholder:

```console
python -I -B ./tools/miw.py run-zucchini --source-directory ./your-zucchini-project --expected-source-root EXACT_SOURCE_ROOT --upstream-commit EXACT_40_CHARACTER_COMMIT --generator Ninja --build-config Release --cmake-define ZUCCHINI_NLOHMANN_JSON_SOURCE_DIR=/pinned/nlohmann-json --cmake-define ZUCCHINI_NLOHMANN_JSON_SCHEMA_VALIDATOR_SOURCE_DIR=/pinned/json-schema-validator --cmake-define ZUCCHINI_LIBFYAML_SOURCE_DIR=/pinned/libfyaml --cmake-define ZUCCHINI_CUCUMBER_GHERKIN_SOURCE_DIR=/pinned/gherkin --cmake-define ZUCCHINI_GOOGLETEST_SOURCE_DIR=/pinned/googletest --cmake-define ZUCCHINI_TPP_BIN_DIR=/pinned/tpp/bin --cmake-define ZUCCHINI_FETCH_TPP=OFF --accept-report PATH_RELATIVE_TO_BUILD/rules.json --allow-trusted-build --out ./evidence/your-zucchini-run
```

3. If you already have report and JUnit bytes, use the read-only path instead:

```console
python -I -B ./tools/miw.py import-zucchini --report ./your-rules.json --out ./evidence/your-import.json
python -I -B ./tools/miw.py bind-junit --report ./your-rules.json --junit ./your-results.xml --out ./evidence/your-junit-binding.json
python -I -B ./tools/miw.py link-junit --report ./your-rules.json --junit ./your-results.xml --binding ./evidence/your-junit-binding.json --out ./evidence/your-linked-execution.json
```

4. Copy `examples/assembly/workbench.bindings.json`, replace the Zucchini tag and
rationale with the real rule, and review it. Keep `standing: PROPOSED`. Then open the
ledger and inspect the obligation:

```console
python -I -B ./tools/miw.py workbench-open --directory ./evidence/invariant-workbench-demo-v8 --bindings ./your-workbench.bindings.json --out ./evidence/your-workspace.json
python -I -B ./tools/miw.py workbench-explain --workspace ./evidence/your-workspace.json --requirement REQ_ACCEPTANCE --out ./evidence/your-obligation-explanation.json
python -I -B ./tools/miw.py workbench-select --workspace ./evidence/your-workspace.json --requirement REQ_ACCEPTANCE --lane ZUCCHINI_REVIEW --out ./evidence/your-selection.json
python -I -B ./tools/miw.py workbench-lower --workspace ./evidence/your-workspace.json --selection ./evidence/your-selection.json --target ZUCCHINI_REVIEW --out ./evidence/your-lowering.json
```

The first useful deliverable is therefore not a new adapter. It is one exact feature,
one exact test execution, and one human-reviewed correspondence to the bounded rule.

## Three acceptance cases to supply

Start with these independent cases so success on one path cannot stand in for the
whole system:

| Case | Concrete observation | What it can support |
| --- | --- | --- |
| Stock refusal | With insufficient required components, the real command refuses and committed state is unchanged | Runtime conformance for that exact build/configuration |
| Successful accounting | With exactly one kit, components are consumed once and finished quantity increases once | Runtime conformance plus comparison to the mathematical twin |
| Unrelated MES rule | A second bounded rule with different state and steps | Evidence that the integration is reusable rather than fitted to one example |

Add concurrent last-kit attempts, duplicate operation IDs, changed-payload reuse,
lost commit acknowledgement, reconciliation, and a bypass attempt before making a
database-level guarantee. The PostgreSQL harness already implements those test shapes;
the work is mapping its reference schema and writer boundary to yours, not reinventing
retry and evidence plumbing.

## Guarantees you can make after the corresponding lane passes

- “This exact Zucchini report was accepted under the declared 2.2.0 profile.”
- “These exact JUnit bytes were explicitly bound and each named scenario linked to a
  non-skipped execution.”
- “This proposed business-rule correspondence was reviewed; it was not inferred.”
- “This exact restricted operation satisfies the stated arithmetic invariant for all
  valid modeled inputs, subject to the named trusted base.”
- “This exact disposable-database campaign observed atomic refusal/success, retries,
  idempotency, reconciliation, and accounting under the named schema and roles.”
- “Any source, contract, binding, engine, or checked-assumption change invalidates the
  old evidence and requires requalification.”

## Guarantees you still cannot make

You cannot claim that the specification is correct, arbitrary C++ is proved, every
production writer is governed, database stock equals physical stock, a passing
scenario is exhaustive, a hash proves meaning, a headless run proves native UI
behavior, or builder-authored courts are independent certification. MIW records those
boundaries instead of concealing them.

## Existing live evidence and next handoff

The package already ran against upstream Zucchini commit
`e8595c9ae94e45c1e28a3effeb7555725c3ac741`: 267 CTest tests passed, 35 report
structures were supported, and four Shop scenarios linked to passed executions in the
pinned Linux/Ninja/Release lane. See `evidence/zucchini-live-acceptance/REPORT.md` and
`RECEIPT.json`. This establishes adapter compatibility for that lane, not acceptance of
your MES application.

For the first real handoff, send only: the immutable export/root and commit, the one
feature and step-definition paths, build generator/configuration, pinned dependency
paths, intended acceptance report path, test name(s), and your proposed business-rule
mapping. The remaining mechanics are already in this package.

Detailed command semantics and refusal conditions are in
`docs/ZUCCHINI-ADAPTER.md`; the complete walkthrough is in `docs/HOW-TO-USE.md`.
