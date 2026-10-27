# What the carried scalar proof establishes

The input subject is the exact accepted Python function source plus the exact
independent requirement contract. The proof path treats that source as data and
does not run it. It symbolically derives all supported path clauses and asks the
unchanged UCM native checker to establish their decision, state and invariant
obligations. Replay repeats lowering and checks every certificate and all exact
bindings. Partial evidence cannot become a complete source proof.

The assembly theorem is over built-in integer parameters a, b, f, q with
nonnegative initial a, b and f. The decision is equivalent to q > 0, a >= 2*q and
b >= q. On acceptance the result is (a-2*q, b-q, f+q). On refusal it is (a,b,f).
All returned stock remains nonnegative. The expressions a+2*f and b+f are conserved.
The pure operation has no loops and every syntactic path returns. This is not a
claim that a remote command will eventually commit or that hardware never fails.

## Explicit trusted components

- The requirement's business meaning and its human approval.
- The new AST validator, Boolean path expansion and contract lowering.
- The inherited UCM contract validator, VC generator, canonical identities and
  Fourier-Motzkin certificate checker.
- The assumed semantics of the supported CPython built-in operations, runtime,
  compiler/interpreter, OS and hardware.

The translator is not formally verified. There is no theorem proving a compiler
correct or arbitrary Python equivalent to these contracts. Regression tests
include a finite 504-input differential comparison for the assembly source; that
is a test of the frontend/interpreter relation, not the universal source proof.
A separate large-integer execution check illustrates that the theorem is not an
enumeration of a small stock range. Serialization still uses UCM's bounded signed
64-bit JSON integer profile; a receipt that cannot be represented refuses rather
than claiming a serialized result. Mathematical integer proof inputs themselves
are not enumerated or bounded to 64 bits.

## Outcomes

`CHECKED_SOURCE_PROOF` means every derived obligation has a checked native
certificate under the declared source subset and trusted semantics. It grants
no authority. `UNKNOWN_PROOF` means at least one obligation remains unresolved;
it is not itself a counterexample. `REPRODUCED_REQUIREMENT_FAILURE` is separate
execution evidence identifying the failed requirement assertion.

The UCM `PROVED` outcome can occur under an explicit precondition. It does not
establish that a caller meets that precondition, that warehouse records are true,
or that code outside the selected source boundary obeys the same rules.

## Excluded claims

No C++ implementation, machine-integer overflow behavior, database transaction,
concurrency schedule, API effect, sensor accuracy, physical warehouse, signed
work-manager custody, hostile-code sandbox, production deployment or full UCM
qualification was proved here. The inherited c3 review remains incomplete and
its c4 obligations remain open. Shipping selected unchanged UCM modules is not a
new UCM release and not a completion of that review.


Turn 4 does not expand the proved language or modify the native UCM checker. New
record-consistency validation, database protocol tests and CTest observations are
not added to the proof's theorem. Changed engine identities require new exact proof
bundles even when the example source and approved business contract are unchanged.
