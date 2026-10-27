# Invariant Workbench implementation codex

This is human navigation, not law, not an invariant registry, and not a generated
constitutional projection. The machine sources are the files under `constitutional/`.

## obligation-ledger

- Role: retain requirement, implementation, subject proof, scenario, execution,
  Zucchini, counterexample, assumption, and external-gate evidence separately.
- Implementation: `src/miw/workbench.py`.
- Operational rule: no evidence class silently promotes another.
- Claim ceiling: a rooted ledger is not specification approval or system correctness.

## realization-space-contract

- Role: describe selectable evidence-space dimensions, realizer capabilities,
  lowering, locks, profiles, and typed refusals.
- Implementation: `src/miw/realization_space.py` and `schemas/`.
- Operational rule: absent, declared, measured, supported, and refused are distinct.
- Claim ceiling: local engineering contract; not a canonical corpus term.

## constitutional-control-surface

- Role: close the operation registry and expose capability/effect/admission metadata.
- Implementation: `src/miw/constitutional.py` and
  `constitutional/OPERATION-REGISTRY.json`.
- Operational rule: plans do not grant execution authority; external effects are explicit.
- Claim ceiling: consumer-owned CGP-shaped realization; no UGK admission.

## independent-operation-commitments

- Role: bind subject, admissibility, meaning, jurisdiction, and receipt vocabularies
  independently in each compiled operation plan.
- Implementation: `compile_operation()`.
- Operational rule: commitment collapse refuses.
- Claim ceiling: commitment integrity is not semantic approval.

## ctr-constitutional-runner

- Role: map every declared local invariant in `CTR-PLAN.json` to one executable court.
- Implementation: `run_ctr()` and `tests/test_constitutional_control.py`.
- Operational rule: declared court coverage is exact and failures remain failures.
- Claim ceiling: builder-authored local courts, not independent review.

## sentinel-receipt-diagnostic

- Role: separate current status, consequential rooted outcomes, and bounded detail.
- Implementation: `cgp_posture()`, `diagnose()`, and the Mosaic Control Surface.
- Operational rule: diagnostics propose observations but perform no repairs.
- Claim ceiling: observability grants no authority.

## headless-application-court

- Role: exercise the actual Mosaic semantic application and controller lifecycle.
- Implementation: `src/miw/headless_runner.py`.
- Operational rule: no shell command strings; Windows helper processes suppress console windows.
- Claim ceiling: no HWND, visual, accessibility, or external-effect proof.

## local-evidence-effect-discipline

- Role: validate, freeze, exclusively create, fsync, and root evidence outputs.
- Implementation: `src/miw/common.py::write_output` and the operation registry.
- Operational rule: existing, aliased, or undeclared outputs refuse.
- Claim ceiling: no database, device, or multi-file crash-atomicity claim.

## self-contract-and-explain

- Role: make MIW's own declared guarantees, nonclaims, assumptions, enforcement
  paths, courts, tests, evidence schemas, and invalidation conditions addressable.
- Implementation: `constitutional/SELF-CONTRACT.json`, `src/miw/self_contract.py`,
  the `self-contract-check` and `explain` commands, and CTR-09.
- Operational rule: every declared court, nonclaim, and trusted assumption must be
  referenced; every enforcement path must exist; tampering or an unknown ID refuses.
- Claim ceiling: this validates a sealed map and its live references. It is not a
  recursive proof of MIW, independent review, semantic approval, or authority.
