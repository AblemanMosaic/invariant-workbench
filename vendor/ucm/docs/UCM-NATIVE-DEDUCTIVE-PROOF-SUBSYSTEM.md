# UCM native deductive proof subsystem v1

This subsystem makes a bounded class of UCM obligations mechanically provable without trusting a model, a solver, or a stored PASS label. It is an experimental native UCM design informed by proof-oriented systems such as Verus, but it does not embed Verus, Rust, Z3, or another proof language.

## Proof path

1. A transition contract binds an exact subject root, obligation ID, sorted integer variables, assumptions, a precondition, statements, and a postcondition.
2. The compiler validates the closed language and deterministically produces verification conditions for assertions, postconditions, loop invariants, and loop termination.
3. Search attempts to derive a contradiction from each condition's antecedents plus the negated goal. Search may be replaced or augmented later.
4. A small kernel replays every input and elimination row in every certificate. Search output is never accepted by assertion.
5. The resulting proof bundle binds the source contract, compiled conditions, assumptions, subject, obligation, and every certificate.
6. The obligation checker permits discharge only for an unconditional `PROVED` bundle with the exact evidence subject. `ASSUMPTION_BOUND` and `UNKNOWN` remain useful evidence but cannot discharge an obligation.

## Language and semantics

The first proof language is intentionally small: mathematical integers represented by bounded source literals and coefficients; linear addition, subtraction and multiplication by constants; conjunction; ordered comparisons and equality; sequential assignment; assertions; and loops with an explicit invariant and decreases term. Loops compile to initialization, preservation, nonnegative-decreases, strict-decrease, and exit obligations.

The current kernel checks explicit Fourier–Motzkin contradiction traces. This is sound for the accepted linear-integer claims because strict integer inequalities are normalized with unit offsets and every accepted certificate establishes inconsistency over the broader rational domain. The search is incomplete: a true claim may return `UNKNOWN`.

## Trust boundary

Trusted proof code is limited to strict contract validation, deterministic VC generation, canonical content binding, and certificate checking. The built-in search procedure is convenient but not authoritative. An external SMT or theorem-prover adapter may receive a rooted solver request, but its response is accepted only when it contains a certificate the native kernel independently checks.

Proofs remain `INFORMATION_ONLY`, have `authority_effect: NONE`, do not open G0, and do not establish real A5. A proof may support an exact constitutional obligation; it cannot grant authority or substitute for custody, identity, execution, or review evidence.

## Agent-facing surfaces

- `COMPILE_PROOF_CONTRACT` returns the rooted verification-condition set.
- `PROVE_DEDUCTIVE_CONTRACT` runs bounded native search and returns `PROVED`, `ASSUMPTION_BOUND`, or `UNKNOWN` with explicit per-condition records.
- `VERIFY_DEDUCTIVE_PROOF` reruns compilation and the kernel against an exact proof bundle.

All three are pure computation surfaces. Raw executable proof tactics, host code, private keys, and effectful adapters are outside their schemas.

## Current limit and next semantic extensions

The v1 language does not model nonlinear arithmetic, arrays, heap aliasing, ownership, concurrency, machine arithmetic overflow, temporal behavior, or effect traces. Those should be added as separate, versioned theories with explicit kernels or reductions. The next useful layer is a UCL contract-to-proof lowering that emits this v1 core for arithmetic invariants while preserving unsupported obligations as explicit residue.
