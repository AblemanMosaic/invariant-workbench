# Constitutional control surface

Status: local consumer-owned engineering candidate; `INFORMATION_ONLY`; authority
effect `NONE`. This surface applies CGP-shaped concepts to the Invariant Workbench.
It is not canonical UGK law, UGK deployment admission, or external certification.

## Roles

| Surface | Workbench role | Claim boundary |
| --- | --- | --- |
| CTR | Maps nine declared invariants to executable local courts and reports exact coverage | Builder-authored courts, not independent review |
| Self-contract | Resolves each public guarantee to code, courts, tests, evidence, invalidation, nonclaims, and trusted assumptions | Structural/live-reference validation, not recursive proof |
| Repair/debug | Derives posture, gaps, and suggested next observations | Read-only advice; never automatic repair or mutation authority |
| Agent capability surface | Lists every exposed operation with capability, effect class, admission, and claim ceiling | Discovery and planning, not execution authority |
| Operation compiler | Lowers an operation to independent subject, admissibility, meaning, jurisdiction, and receipt commitments | A plan cannot authorize itself |
| Effect discipline | Validates then exclusively creates canonical evidence and returns its root | Local create-only evidence; not database or device atomicity |
| HeadlessRunner | Exercises the actual Mosaic semantic tree and controller flow without shell interpretation or a visible console | No HWND, visual, accessibility, or external-effect claim |

## Sentinel, Receipt, Diagnostic

These are observability levels, not interchangeable verdicts.

1. **Sentinel** is the current bounded summary: health, known gaps, blockers, and
   freshness. It may be volatile or exported as a snapshot.
2. **Receipt** is the rooted outcome of a consequential operation. It preserves the
   exact claim ceiling and is evidence, never authority.
3. **Diagnostic** is bounded explanatory detail and a suggested next observation.
   It performs no fresh external contact unless a separately admitted operation does so.

## ESA, EVS, COP, and SRSA

- ESA makes the exact workspace root, capability inventory, open assumptions, and
  known gaps legible.
- EVS revalidates proof, example, and imported execution receipts while preserving
  each evidence class.
- COP projects Sentinel, Receipt, and Diagnostic state and exposes contention or
  incompleteness without turning observation into permission.
- SRSA bounds reliance: open physical-stock, writer, transaction, and semantic-approval
  assumptions keep the posture defeasible and suggest only a next observation.

The currently referenced UGK line supplies native CGP/ESA/SRSA/CTR/HeadlessRunner
concepts. This package does not vendor or invoke that runtime. Its EVS and COP surfaces
are explicitly MIW-owned downstream realizations.

## Independent commitments

`compile-operation` emits:

- `h_s`: exact subject and inputs;
- `h_c`: admission and effect class;
- `h_m`: operation meaning and claim ceiling;
- `h_j`: surface, requester, and locality;
- `h_r`: receipt schema and terminal outcome vocabulary.

The historical “Three Hash Rule” name must not be used here to collapse these five
commitment domains. The compiler refuses a plan whose commitments collapse.

## Effect inventory

Every CLI and Mosaic operation is present in
`constitutional/OPERATION-REGISTRY.json`. External effect classes—loopback model,
trusted process, disposable database, and compiler execution—require explicit opt-in
or an external gate. The control surface exposes no generic command runner, arbitrary
selector, hidden repair, or execute-by-plan route.

Current EffectAtomicity is intentionally narrow: validate inputs, freeze canonical
result bytes, create a new non-aliased output exclusively, flush/fsync, and return the
root. Multi-file crash inseparability, PostgreSQL transactions, C++ process behavior,
and device effects retain their own protocols and acceptance gates.

## Commands

```console
python -I -B ./tools/miw.py capability-surface --out ./evidence/capabilities.json
python -I -B ./tools/miw.py self-contract-check --out ./evidence/self-contract-check.json
python -I -B ./tools/miw.py explain --out ./evidence/self-contract-index.json
python -I -B ./tools/miw.py explain --id G-EVIDENCE-CLASS-SEPARATION --out ./evidence/evidence-class-explanation.json
python -I -B ./tools/miw.py headless-application --directory ./evidence/qualification/demo --bindings ./examples/assembly/workbench.bindings.json --out ./evidence/headless-app.json
python -I -B ./tools/miw.py constitutional-test --directory ./evidence/qualification/demo --bindings ./examples/assembly/workbench.bindings.json --out ./evidence/ctr.json
python -I -B ./tools/miw.py cgp-posture --workspace ./evidence/workspace.json --proof-receipt ./evidence/proof-run.json --bdd-receipt ./evidence/bdd-run.json --headless-receipt ./evidence/headless-app.json --out ./evidence/posture.json
python -I -B ./tools/miw.py diagnose-workbench --posture ./evidence/posture.json --out ./evidence/diagnostic.json
```

`compile-operation` additionally requires JSON `--subject` and `--inputs` objects.
Its output says `execution_authority: NOT_GRANTED_BY_PLAN`.
