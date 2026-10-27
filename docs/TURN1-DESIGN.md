# Mosaic Invariant Workbench
## Design proposal and bounded construction outline

Status: DESIGN_PROPOSAL. The software described here has not been built or verified in this session. This proposal does not revise or release UCM c4, complete its independent review, or grant operational authority.

Working name only. No release version assigned.

## 1. Product decision

Build a local-first workbench that lets a developer define an important business guarantee, obtain a statically checked implementation of a small operation, integrate it behind an explicit effect boundary, and maintain the connection between meaning, code, evidence, and deployment assumptions through change.

The first demonstration must answer the MES developer's request for a proof before execution. The system-wide dependency map is a second, independent benefit. A runtime guard, many passing tests, an AI review, or a hash linking a proof to source cannot stand in for a proof that the actual source satisfies the stated contract.

The primary user should not need to adopt an entire operating system, replace an MES, or learn all constitutional terminology. The first unit of adoption is one business operation. The next is a related group of operations sharing an invariant.

## 2. What the uploaded UCM handoff supplies

The supplied c4 handoff contains a native deductive proof subsystem, including declarative transition contracts, deterministic verification-condition generation, bounded proof search, and a certificate-checking kernel. Its agent surfaces include COMPILE_PROOF_CONTRACT, PROVE_DEDUCTIVE_CONTRACT, and VERIFY_DEDUCTIVE_PROOF.

Its documented theory is linear arithmetic over mathematical integers, with sequential assignments, assertions, and restricted loops with invariants and decreases terms. The search is incomplete. Failure to obtain a certificate can mean UNKNOWN, not that the claim is false.

Its current proof language does not include general conditional statements, arrays, maps, heap ownership, concurrency, machine-integer overflow, temporal behavior, or effect traces. The documentation identifies UCL contract-to-proof lowering as a useful next layer, not a completed general correspondence theorem.

Native outcomes distinguish PROVED, ASSUMPTION_BOUND, and UNKNOWN. The word PROVED still concerns a theorem under its declared precondition and trusted semantics. It does not establish that a caller meets the precondition, that external data is truthful, or that a hash-bound program implements the contract.

The workbench also supplies exact source and task bindings, bounded candidate preparation, candidate-bound test execution, impact/lane machinery, custody and recovery protocols, and a non-semantic progress channel. Work-plan completion does not automatically discharge arbitrary product requirements.

The carried c3 independent review is INCOMPLETE_REVIEW, with required Tier 1 work outstanding. c4 remains experimental and information-only, with authority_effect NONE, real_a5 false, and G0 closed. Those limits remain attached to its use here.

## 3. Product shape

The product would contain a local desktop interface, a command-line interface, and a headless CI runner over one shared engine. A native Mosaic UI is appropriate for the desktop application. The interface should start with a simple Rule, Code, Evidence view; the dependency map should be available without dominating the first experience.

AI assistance is optional. Local models can draft rules, suggest invariants, explain verification failures, and propose changes. A model is never the proof checker, the business-rule owner, or the release authority. Normal operation should not require hosted AI or telemetry.

Two entry points are needed:

1. Proof-first: define and verify one operation before connecting any database.
2. Existing-system assessment: import selected source and schema information, propose a dependency map, and identify which guarantees lack evidence or a closed effect boundary.

The second mode must not advertise enforcement. A read-only map cannot prevent an existing application from writing invalid state.

## 4. The MES developer's first workflow

### 4.1 Select one boundary

He opens a local project and selects the assembly operation, related inventory schema, and relevant Gherkin scenarios. Imports are explicit and read-only by default. The tool does not execute an unfamiliar repository merely because it was imported.

The assistant proposes a model and lists unresolved questions: when stock is reserved, when it is consumed, which recipe version governs a work order, which process can adjust stock, and whether a recorded completion represents a physical event or only an accounting transition.

Discovery produces candidate facts. It cannot establish that every possible writer or integration has been found. Missing edges remain visible and prevent narrow whole-system claims.

### 4.2 Approve the meaning

The original rule is ambiguous: a work order might legitimately finish after its components have already been consumed. Empty shelves at completion are not necessarily a violation.

For the first demonstration, choose an intentionally simple operation that consumes components and records finished output together. For a later production lifecycle, use an invariant such as: every recorded completed work order has sufficient, non-reused consumption assigned to it under its approved recipe version.

The workbench stores the plain-language requirement, precise contract, units, scope, assumptions, examples, and named owner together. A semantic change is an explicit review event, not a side effect of AI code repair.

### 4.3 Inspect the proposed operation

Use a fixed recipe of two A components and one B component per finished unit. Let a, b, and f be nonnegative mathematical integers, and q be the requested integer quantity.

Readable pseudocode, not an already implemented UCM syntax:

```text
assemble(a, b, f, q):
    if q <= 0:
        return Refused(a, b, f)
    if a < 2*q or b < q:
        return Refused(a, b, f)
    return Accepted(a - 2*q, b - q, f + q)
```

The target proof obligations are:

- For every valid input state and integer q, the operation terminates with a defined result.
- It accepts exactly when q > 0, a >= 2*q, and b >= q.
- On acceptance, output stock increases by q and inputs decrease by exactly 2*q and q.
- The returned stock remains nonnegative.
- On refusal, modeled business state is unchanged.
- In this closed assembly model, a + 2*f and b + f are conserved.

The acceptance equivalence matters. A program that always refuses satisfies a weak no-invalid-assembly property but does not implement the intended operation.

A finite source literal or certificate-size limit is not an input-enumeration bound. Conversely, mathematical-integer reasoning does not automatically establish behavior of a bounded database integer or machine integer. Representation and conversion obligations must be added at integration.

### 4.4 Prove before execution

The first proof demonstration should run without a database, API, or sample warehouse. The source body and its postconditions are verified symbolically, with exact verifier inputs, versions, options, and logs retained.

For initial delivery, use the existing UCM native checker for the arithmetic obligations and a pinned established program verifier, such as Dafny, for the complete guarded executable function. This avoids expanding the native theory just to demonstrate ordinary branches. The business-source translation and any native lowering are still explicit correspondence obligations.

A Dafny result is backend-specific evidence. It is not automatically a certificate accepted by UCM's native kernel. Adding an admissible backend evidence class requires an explicit policy/checker contract. Alternatively, a result can remain useful information without discharging a native obligation.

The proof-critical source should avoid unproved external methods. Verification-disabling options and hidden axioms must be rejected or reported as explicit holes. A zero exit status is insufficient if it verified only a filtered subset of the required methods.

Native-only execution is a later option after a guarded transition language, its lowering, and its execution correspondence have supporting evidence. Do not present a hash binding as that evidence.

### 4.5 Understand failures

A failed attempt should show the affected guarantee and the obligation that remains open. A backend-produced counterexample is useful when available, but the native search's UNKNOWN result must not be rendered as a counterexample.

Include benign defective variants in the demonstration: increment output without consuming input, consume the wrong quantity, mutate state on refusal, and refuse every request. Their rejection helps make the property understandable but is not the proof of the correct implementation.

Check that the precondition has valid witnesses and that accepted behavior is reachable. Review any strengthened preconditions. Moving a difficult requirement into a precondition can make a theorem easier while making the application guarantee weaker.

### 4.6 Export an evidence-bearing component

The export contains approved requirement and contract, verified source, generated artifacts, exact toolchain inputs, native certificates where available, backend-specific verification evidence, assumptions, unresolved obligations, and a replay procedure.

Generated code should not be manually edited while retaining the previous claim. Either regenerate from the approved source or treat the edited code as a new subject requiring its own evidence.

A verified component does not verify its caller. The integration needs to establish valid inputs, controlled shared-state access, correct conversions, and use of the verified operation for every relevant effect.

## 5. Database integration

The first reference adapter should support one explicitly pinned PostgreSQL configuration, not all databases at once. It should bind schema versions, columns, units, roles, isolation policy, operation identifiers, and the command's payload.

The intended transaction reads and validates relevant state, computes the verified transition, applies the component/output changes, and records the operation outcome within one database transaction. A stable operation identifier is bound to the complete canonical request, tenant, and operation version. The same identifier with different content is refused.

Duplicate concurrent requests require a database-enforced uniqueness/coordination design, not just a prior SELECT. A repeated completed request returns its recorded outcome. Serialization failures restart the whole transaction, including reads and guard evaluation, under the same business request identity.

Serializable execution provides a useful abstract boundary, but the concrete adapter still needs a correspondence argument. Tests for races, crashes, and retries are integration evidence, not a substitute for a proof of every possible execution.

The effect boundary must include all writers to protected state. Direct administration, other services, import jobs, migrations, and repair tools cannot be ignored. If another writer remains outside the admitted protocol, the claim is limited to operations through the protected interface. It is not a guarantee about the whole database.

Administrative intervention cannot be made impossible merely by application policy. Maintenance procedures should explicitly suspend the affected operational claim, record the intervention, and require reconciliation/requalification before restoring it.

Add representation checks for maximum values, units, rounding policy where relevant, and arithmetic conversions. A refusal can leave business tables unchanged while still creating an audit record. Define the exact state covered by no-change claims.

A timeout around commit can leave the outcome unknown. Reconcile using the durable operation identity instead of describing uncertainty as a definite refusal.

## 6. API integration and physical reality

External effects need separately modeled intent, dispatch, acknowledgement, and reconciliation. The local database cannot by itself guarantee that a remote system performed an action exactly once.

A transactional outbox can atomically record local changes and delivery intent. The recipient's behavior, duplicate handling, retry policy, and acknowledgement semantics remain separate obligations.

Operational outcomes should distinguish acceptance, business refusal, invalid input, retryable conflict, unknown effect outcome, and reconciliation required. Proof outcomes are a different vocabulary. UNKNOWN_PROOF does not mean UNKNOWN_REMOTE_EFFECT.

Physical inventory accuracy remains an empirical assumption supported by counting, sensors, reconciliation, and operational procedures. A proof about records does not prove that parts physically existed or that an uncontrolled machine could not assemble something.

## 7. Expand from assembly to a real work-order lifecycle

After the scalar demonstration, add received stock, available stock, reservations, consumption assigned to work orders, scrap, completion, cancellation, and authorized corrections as separate operations.

The useful stronger claims concern resource accounting and ownership of allocations: no double reservation, no reuse of consumption, no completion without required recorded inputs, and no silent inventory creation by an adjustment path.

These claims require richer structures and theories than current native linear arithmetic alone. Fixed recipe coefficients allow linear arithmetic; multiplying two unrestricted variables, arbitrary maps of stock items, or temporal progress needs additional treatment. The UI must identify unsupported theory rather than silently sample it.

Progress is separately specified. Proving a finite operation terminates does not prove that a submitted job eventually commits under endless contention, network failure, or scheduler starvation. Any eventual-completion claim must state its environmental assumptions.

## 8. The dependency and evidence map

The map links:

```text
business rule
  -> formal invariant and preconditions
  -> executable source and proof obligations
  -> verification evidence and trusted tools
  -> compiled artifact
  -> schema, transaction adapter, and writer permissions
  -> external service/environment assumptions
  -> deployed identity and current observations
```

Edges are typed: implements, refines, assumes, verifies, writes, authorizes, depends-on, and invalidates. Each node retains its exact subject and version. A map assembled from incomplete discovery is explicitly partial.

Useful questions are: why is this guarantee believed, what code implements it, which unproved boundary remains, what does this change invalidate, and who can authorize the affected transition?

The map is not an omniscient representation of an entire company. It is an inspectable account of a declared scope and its open boundaries.

## 9. Evidence and decision semantics

Do not compress all assurance into one PASS. A guarantee view should distinguish specification approval, formal proof, source correspondence, compilation trust, integration testing, operational boundary checks, empirical assumptions, and release authorization.

Evidence records need at least the claim ID, exact subject identity, scope, formal statement, preconditions, environmental assumptions, evidence kind, checker identity, result, unresolved obligations, and dependency edges. Toolchain inputs and relevant configuration must be pinned. Replaying old evidence must not silently make it current evidence for a changed subject.

For future product semantics, useful categories include CHECKED_PROOF, ASSUMPTION_BOUND, CHECKED_WITHIN_BOUND, TESTED, UNKNOWN, COUNTEREXAMPLE_FOUND, UNSUPPORTED, and STALE_FOR_CURRENT_SUBJECT. These are proposed product classifications, not a claim that c4 already exposes these exact labels.

A bounded exhaustive check can establish a property of its specified finite model. It does not thereby establish the unbounded application property. Preserve the bound in the claim.

A cryptographic identity establishes which bytes are referenced. It does not establish correctness, trustworthy authorship without additional identity evidence, freshness without an external expectation, or semantic correspondence between different representations.

## 10. AI participation

The assistant can draft model candidates, generate examples, suggest invariants and lemmas, propose repairs, explain proof obligations, and prepare candidate trees. Those actions remain reviewable proposals.

It cannot silently weaken a requirement, strengthen a precondition, drop an obligation, insert an assumption, mark a method as verified without checking it, promote tests to proofs, or authorize deployment. An AI explanation is not evidence of the claimed theorem.

Unknown results can lead to a clearer invariant, a richer explicitly admitted backend, a smaller claim, or a human investigation. The tool should not respond by relabeling uncertainty as success.

## 11. Changes and ordinary maintenance

When a recipe, schema, API contract, implementation, or verifier changes, compute the affected dependency closure. Missing dependency information forces conservative requalification rather than an optimistic light lane.

A recipe change from two A units to three should identify the transition arithmetic, allowed-input conditions, tests, open work orders, and migration policy affected. Existing work orders may remain tied to their original recipe. Any migration needs its own approved rule.

Developers can retain a pinned working version. Newly discovered limitations or changed environment assumptions still affect what may honestly be claimed about that version. Version sovereignty does not mean freezing the truth of an assurance claim.

CI should return structured results and human-readable explanations from the same evidence. The final release package is separate from both an AI summary and a progress display.

## 12. How UCM governs construction

Use c4 as a pinned experimental construction substrate, not as a claim that the resulting application is verified or production-authorized. Preserve the original archive unchanged and create a separately named candidate project.

A project charter should define the selected product scope, allowed local effects, forbidden production effects, trusted tools, immutable input pins, human approval roles, proof requirements, and unresolved inherited limits.

Use existing read/orientation, impact/lane, task custody, bounded worker, and proof surfaces where their schemas fit. Do not invent evidence that an actual UCM work plan was executed merely because this design maps to its operations.

Candidate work should be staged in disposable locations. Every test or proof result binds the exact candidate, checker/toolchain, case identity, and applicable contract. Candidate code requires appropriate external sandboxing; the UCM worker is not itself an OS security boundary.

Retain the distinction between an observed filesystem/process effect and constitutional authority. Use fixture identities only as fixtures. No production signer or deployment permission is inferred from bundled examples.

Progress remains observational. A displayed completion percentage or model-written summary cannot produce a semantic verdict.

Keep product validation and independent UCM review separate. Missing inherited review legs remain open even if the inventory demonstration succeeds.

## 13. Batched construction roadmap

### Batch A: proof-first demonstration

Build the approved scalar assembly requirement, full guarded source, pinned verifier adapter, native arithmetic obligations, evidence export/replay, explicit trust report, and non-vacuity checks. Include a small set of defective variants that illustrate the contract.

Acceptance: the entire guarded function has a statically checked contract, valid calls can succeed, refusal preserves the declared state, verification scope is complete, and evidence can be replayed without a database. The first shareable artifact should fit a developer's inspection, not require adopting the full platform.

### Batch B: usable local workbench

Build the local UI, CLI, canonical rule model, obligation ledger, evidence classification, optional AI proposal interface, graph view, import/export, and CI integration in one coherent batch.

Acceptance: another developer can define a second resource-accounting operation, inspect its exact claim, obtain appropriate evidence, and see what an edit invalidates. Unsupported claims remain explicit.

### Batch C: one real effect boundary

Build the PostgreSQL reference schema/adapter, operation-identity protocol, bounded transaction model, writer-boundary checks, numeric conversions, rollback/retry/reconciliation logic, and integration/failure-recovery tests.

Acceptance: evidence separately reports verified core, transaction-model results, implementation correspondence status, integration tests, trusted DB/configuration assumptions, and remaining bypasses. No end-to-end proof label is issued merely because the concurrency tests pass.

### Batch D: lifecycle and pilot

Add reservations, consumption assignment, completion/cancellation, versioned recipes, and a read-only or shadow pilot before granting production effects. Preserve privacy by using synthetic or explicitly authorized data.

Measure time to first useful proof, human specification effort, repair effort, proof replay cost, maintenance cost after a realistic change, runtime overhead, and whether an independent developer understands the claim. A lower-cost claim is a result to measure, not a premise.

Freeze one exact candidate for scoped independent review, consolidate findings, prepare one repair successor, and requalify before a separately authorized disposition. Do not conflate that product review with completion of c4's inherited review obligations.

## 14. Initial exclusions

Do not promise arbitrary legacy-code verification, every database, arbitrary distributed transactions, inferred business truth, physical-machine safety, automatic discovery of all writers, or an already verified compiler/runtime stack.

Do not require an MES rewrite, a hosted account, a new production operating system, or a general language rewrite to benefit from one verified component.

## 15. Other users

The same approach can support booking capacity, quota allocation, approved document publication, bounded transfers in an internal ledger, and construction-material allocation. Each domain needs its own precise invariants and external assumptions. Reusing a proven pattern is conditional on a checked instantiation and compatible composition, not simply similar wording.

## 16. Handoff inspection performed for this proposal

Archive: UCL-UCM-AGENT-WORKBENCH-c4-INDEPENDENT-REVIEW-HANDOFF.zip

Computed SHA-256:

```text
6bb3d7eb05cfb830d9dbe4253be5326ce67f7b306c6646b94107a321e355cd69
```

Seven declared outer members were checked against the supplied manifest. Nineteen selected reconstructed source/document files were compared with their FULL_DEVELOPMENT profile hashes. These are internal byte-consistency checks, not independent out-of-band identity authentication.

Relevant source read: the native proof documentation, native proof implementation and tests, agent interfaces, project-management and interface-limits documents, c4 overview, and carried c3 review.

No full qualification, independent review, new proof demonstration, or product implementation was executed. The original archive was not modified.

## 17. Primary technical references

UCM references are paths within the supplied archive's reconstructed source:

- docs/UCM-NATIVE-DEDUCTIVE-PROOF-SUBSYSTEM.md
- src/uclop/deductive_proofs.py
- docs/WORKBENCH-C3-AGENT-INTERFACES.md
- docs/WORKBENCH-C1-PROJECT-MANAGEMENT.md
- docs/WORKBENCH-C1-INTERFACES-AND-LIMITS.md
- docs/WORKBENCH-C4-OVERVIEW.md
- reviews/awb-c3/REPORT.md

External documentation consulted for proposed integration choices:

```text
Dafny reference manual:
https://dafny.org/latest/DafnyRef/DafnyRef

PostgreSQL transaction isolation:
https://www.postgresql.org/docs/current/transaction-iso.html

Quint model-based testing and trace validation:
https://quint.sh/docs/model-based-testing

AWS idempotent API guidance:
https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/

AWS transactional outbox guidance:
https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html
```
