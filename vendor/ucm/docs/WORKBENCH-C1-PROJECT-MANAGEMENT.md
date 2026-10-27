# Bounded project management and portable continuity

`src/uclop/workbench_manager.py` is the supported coordinator for real, bounded
local work. The original Project Intelligence and simulated Autonomous Project
Manager overlays remain byte-exact compatibility/reference inputs. The manager
calls their existing project, impact, exact task-coverage and dependency
validators; it does not create a second project graph implementation.

## Scope and claims

Three work operations are supported: `INSPECT_ARTIFACTS`, `RUN_TESTS`, and
`PREPARE_CANDIDATE`. The worker independently pins the source bytes, exact test
module bytes and identities, issuer, registry, policy and operation contract.
Edit preparation creates a disposable proposed tree; it does not apply it to the
canonical source. Trusted tests run in an isolated Python invocation, with their
actual result and observation receipts. This is not an operating-system sandbox.

The manager can report `COMPLETE_INFORMATION_ONLY` only when every plan task has
an authenticated, re-derived passing worker receipt for its exact request. That
claim means the selected work plan ran. It does not satisfy arbitrary human
requirements, grant standing, accept a design, qualify the whole project, release
an artifact, or mint constitutional authority. `project_obligations_satisfied`
remains empty. A model-authored plan or summary cannot substitute for execution.

All manager and capsule results retain `standing: INFORMATION_ONLY` and
`authority_effect: NONE`. Worker receipts separately report observed local
filesystem/process effects. Production, network, account creation, host security
changes, deployment and real A5 are outside these operations; G0 stays closed.

## Plans and exact coverage

`create_plan(project, pins=..., task_actions=..., selected_change_ids=...,
budget_limit_units=...)` adapts the original APM proposal. `task_actions` maps
every affected PI record ID to exactly `{operation, payload}`. The proposal's
dependency edges, coverage set and source binding are revalidated. Callers cannot
remove an affected task, drop an edge, add a duplicate task, or replace its
source record while keeping a passing plan root.

Pins are mandatory for project snapshot, source snapshot, charter, grant,
registry, policy and jurisdiction. Each execution request also binds the exact
tenant, operation ID, task ID, attempt ID and generation. Unknown or incomplete
impact never reduces assurance. The PI graph does not cover every possible
runtime dependency, so its plans require `QUALIFICATION` and permit no evidence
reuse or lighter-lane downgrade. It is planning input, not a completeness proof.

Each store uses one immutable plan. The initial store is generation 1; changing
the plan, source, charter or grant requires the explicit signed successor
transition described below. It cannot silently reuse the previous plan's
idempotency history or completion.

## Orientation and public API

Construction requires a verified orientation and its separately supplied
external pins, an exact public worker identity, and a pinned worker policy root:

```python
manager = WorkbenchManager(
    store,
    project=project,
    plan=plan,
    orientation=orientation,
    orientation_pins=external_pins,
    worker_identity=worker_identity,
    worker_root=worker_policy_root,
    expected_head={"sequence": 0, "head": "GENESIS"},
    now=current_trusted_time,
)
```

The charter/grant, source/project/registry/policy pins, jurisdiction, tenant,
capability membership and expiration are checked. The orientation's ceremony
head remains an immutable ceremony input; the protected manager head is checked
separately on every operation. A distinct session may resume the same project
only with a valid corresponding orientation and the exact current external head.

`manager.current_head` is the result of that object's latest successful open or
write. It is never an automatic freshness selection. An orchestrator must retain
and supply `{sequence, head}` from its external custody. The store's local anchor
and old signatures are not a substitute for that external expectation. Time is
also an externally trusted input; this library does not authenticate a clock.

Public methods:

- `status(expected_head=..., now=...)` folds the signed stored events again.
- `begin_dispatch(task_id, operation_id, dispatcher_id, expected_head=..., now=...)`
  persists the exact in-flight request and consumes budget before work starts.
- `complete_dispatch(ticket, result, expected_head=..., now=...)` independently
  validates and folds the real worker result.
- `execute(...)` composes begin, worker callback and completion for ordinary use.
- `mark_uncertain(...)` retains an interrupted attempt without asserting success.
- `reconcile_not_executed(...)` consumes an exact worker-signed `NOT_EXECUTED`
  attestation. It permits a bounded new attempt under a new operation ID; the
  original attempt and its budget remain recorded.
- `reopen_recovering_store(...)` completes only an authenticated interrupted
  storage transaction. It never invokes a worker.
- `export_capsule(...)` signs exact state, journal and anchored head.
- `import_capsule(...)` verifies and stages that exact capsule under the same
  externally held head. It does not roll the anchor backward or advance it.

Private keys never appear in these requests. `ProtectedStateStore` and the worker
use the custody provider's opaque handles. The published deterministic identities
in tests are fixtures and provide no real identity seating.

## Concurrency, idempotency and interruption

Every mutation acquires a local nonblocking OS file lock and checks the external
expected head again before reading the protected store. The lock is released on
process exit; it is a synchronization mechanism on a trusted local filesystem,
not a security sandbox. The anchored commit performs the state/journal CAS.

Only one persistent dispatcher lease may be active. Another dispatcher with an
old head is refused; one with the current head still cannot start a second task
until the active attempt is reconciled. Dependency tasks must already be
complete. Budget is charged before worker execution and is not refunded by
interruption. Each task's attempt count also stays within the grant.

An operation ID is bound to the complete original request. Replaying a completed
operation returns its prior authenticated material without invoking the worker.
Reusing it for a different task, payload, subject or generation refuses. Replaying
an in-flight or uncertain operation requires reconciliation rather than retry.

Crashing before a worker and crashing after it can be indistinguishable to the
manager. Both retain `IN_FLIGHT` custody. The safe exits are an exact valid result
already recorded by that worker, or a worker-authenticated statement that no work
executed. Caller assertions and unsigned status dictionaries do not clear the
lease. A failed real result is recorded `FAILED`, never converted to completion.

The signed state is folded from its events on open, status, mutation and capsule
import. Folded task/status fields are not stored as self-certifying PASS labels.
Tampering with signed payloads, restoring old state against a newer anchor,
deleting journal history or substituting the worker root is refused.

## Portable handoff

A capsule contains exact signed state and journal rows, pins and the current
head, all signed by the store custody identity. Import independently verifies
the snapshot in a temporary directory, including every embedded worker receipt,
before installing it. The destination's external anchor must already name that
same exact head. Existing destination files must be absent or byte-identical,
which permits completing an interrupted exact copy without overwriting a fork.

An older authentic capsule remains stale under a newer external pin. Moving an
anchor to an older head is outside this API. A deployment of the library must
provide trustworthy custody/anchor storage; a user-editable local anchor cannot
prove freshness against its own administrator.

## Explicit plan/source/charter succession

`workbench_migration.py` provides a versioned transition between immutable plan
generations. It supports updated project/source, charter/grant and worker/state
identities under the same independently pinned project ID, tenant and Governor.
Governor rotation needs a separate delegation contract and is refused here.

`prepare_migration(...)` reads the exact current source head and produces public
unsigned authorization material. It includes both identity/pin sets, the new
plan root and logical store namespace, the exact prior head and sequence, all
authenticated completed work receipts, pending tasks and pending verification
obligation records. Active or uncertain work blocks migration.

`authorize_migration(...)` is the opaque external-Governor signing adapter.
Production callers must use their already authorized custody provider; the
published fixture issuer seats no actual Governor. The resulting signature
binds the full source and target inventories. Dropping or adding a completed
receipt, changing the tenant/project, substituting a source or target identity,
or reusing a generation refuses.

`migrate(...)` requires both externally held heads. It first consumes the current
old head exactly once and writes a signed terminal migration state. The old
manager then refuses further work, preventing a fork or reuse of that generation.
Only then is the authorized successor initialized. Its payload embeds verified
predecessor custody: source capsule/project/orientation, the signed migration
authorization, and the terminal state and journal row. Every reopen, capsule
import and state fold revalidates that chain, including the historical worker
receipts and the exact preserved inventories.

Old completions are historical evidence only. New-generation tasks start
`PENDING`, spend no inherited budget and require their own exact worker receipts.
No old verification obligation is silently accepted for a changed subject.

A durable migration intent is written in the destination store before consuming
the old head. `resume_migration(...)` handles an interrupted child initialization
under the caller's current old-terminal and destination heads. It reconciles
only that exact authorization; it neither creates a substitute genesis nor
repeats work. A replay after the destination already exists returns the same
verified successor. Altered destination state or a different authorization is
refused.

The local serialization locks prevent concurrent consumers of the same selected
anchors. External custody must preserve the logical destination namespace and
head: creating a replacement "fresh" anchor behind the library is not a valid
freshness proof. The c1 chain is explicitly bounded to six generations by the
current canonical-value budget; extending it requires an explicit contract
revision or a content-addressed detached-history representation.

## Acceptance coverage

`tests/test_workbench_manager.py` exercises actual inspect/test/edit-proposal
receipts; exact plan coverage and dependency checks; partial-graph downgrade
refusal; stale/replaced state; two-session concurrency; repeated and aliased
operation IDs; forged and signed wrong-subject receipts; interrupted work before
and after execution; signed no-execution reconciliation; budget exhaustion;
tenant, jurisdiction and worker policy mismatch; exact portable import; and an
interrupted protected-store commit. Full qualification is performed by the
root workbench campaign after composition.

`tests/test_workbench_migration.py` additionally checks changed-source succession,
unchanged historical receipt preservation, independent target task completion,
same-generation fork refusal, old-head staleness, in-flight/uncertain holds,
wrong Governor/project/tenant, altered completion inventories, interrupted child
commit recovery, portable successor import and a multi-generation predecessor
chain.
