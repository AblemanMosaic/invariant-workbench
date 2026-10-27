# Turn 4 architecture

The readable specification, its formal interpretation, the operation source,
observations, proofs and permission to act remain separate objects.

```
Native scalar scenarios / Zucchini report inputs / model proposals
                    |
       strict parsing, identity and scope checks
                    |
     requirement and evidence relationship model
       /            |               \
UCM proof kernel   BDD observations  partial impact map
                    |
      local qualification and candidate inspection
                    |
    optional, explicitly admitted effect adapters
```

The actual UCM kernel, evidence checker and obligation-conservation modules remain
unchanged from the exact c4 input. Turn 3 includes an additional unchanged closure
for WorkbenchManager, BoundedWorker, protected state, orientation and migration.
`vendor/ucm/TURN3-CLOSURE.json` binds those files. The fixture campaign invokes real
interfaces; it does not assert that the entire product build was dispatched under
a production UCM grant. Model-authored reports cannot discharge arbitrary obligations.

## Three application paths

1. Native scalar path: restricted source -> paths -> UCM arithmetic obligations ->
   checked certificates. No executing the example to discover its theorem.
2. Zucchini path: exact report -> semantic validation -> coverage observation;
   separately bound JUnit -> execution observation. A failure is not automatically
   attributed to a particular requirement. Actual upstream build is a separate lane.
3. Work-order path: validated state -> pure transition -> optional transaction adapter.
   This richer model has tests and a finite-state exploration, not the scalar proof.

## Lifecycle

Available stock, reservations and consumption assigned to an order are distinct.
Only consumed work can complete. Shelf stock may be zero at completion because
consumption has already been attributed. No consumption can be assigned by the API
to two orders. Cancellation returns only unconsumed reservations. Consumption reversal,
scrap, substitution and rework are unsupported, not silently approximated.

Recipe revision identifiers are immutable. Adding r2 does not rewrite r1 or an
existing order's recipe root. Exact accounting is checked on every input and output
state. Integers are bounded to signed BIGINT magnitude for the reference representation.
The JSONB storage is not itself a database-side proof of these invariants.

## PostgreSQL boundary

One SERIALIZABLE transaction locks the tenant state row, checks an operation receipt,
computes the pure transition, and atomically records state plus receipt. The coarse
lock sacrifices throughput for a small reference boundary. Serialization/deadlock
errors retry the whole transaction with a fixed request identity and finite budget.
A commit acknowledgement loss returns uncertainty and requires reconciliation.
A missing receipt is NOT_OBSERVED, not proof of nonexecution.

The caller's DB role is a trusted writer. PUBLIC privileges are revoked by the setup
SQL, but this does not prevent that role, administrators, migrations or other services
from making bypass writes. No all-writer or end-to-end concurrency theorem is claimed.

## Agent and model boundary

A proposal binds exact contract, source, target requirement and checking-basis root.
Only native scalar scenario text is accepted. Its meaning is checked by the existing
oracle and its failure is reproduced on the restricted source. It cannot edit code,
change rules, approve the specification, grant release authority, or turn no result
into a proof. Ollama is optional and loopback-only at the client transport level.
Whether the local service itself relays to another service is a deployment assumption.

## Actual UI

The retained input in `foundry/source/` is compiled by the unchanged Mosaic Foundry.
HEADLESS owns semantic state; WIN32 realizes the same closed interactions.
Navigation is the only declared operation. Viewing evidence cannot issue a model
request, change code, connect a database or deploy an application. Packaged integration
summaries are labeled builder observations; native scalar proofs are rechecked before
being displayed. This is a read-only native viewer, not yet an interactive IDE.

The original sun PNG is retained and hash-bound. No fonts are shipped. The upstream
metadata discrepancy (distribution 0.2.0rc1 versus module 0.1.0) is disclosed, not repaired.
