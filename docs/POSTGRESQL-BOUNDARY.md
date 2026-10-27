# PostgreSQL reference boundary

Status: implementation and fault-driver tests supplied; live PostgreSQL NOT_RUN.

The implementation is `src/miw/postgres.py`. The schema is `sql/reference.sql`.
Only explicit caller admission creates a repository or runs setup. No DB connection
occurs during import, viewer startup, pure demonstrations or ordinary regression.
The optional live campaign requires an explicit flag and MIW_TEST_PG_DSN.

A command binds tenant, stable operation ID, action and complete payload. In one
SERIALIZABLE transaction the adapter locks the tenant state row before reading any
receipt for the operation, validates state, computes the pure transition and stores
state and receipt together. A repeated exact command returns its existing receipt.
Reusing an operation ID with a changed payload is refused. Business refusals leave the
modeled state unchanged but may store a durable refusal receipt, which is an audit effect.

The reference intentionally serializes all writes within a tenant. It is not a
high-throughput architecture or a claim that every business application needs this design.
Inputs are genuine Python integers, not bools, and bounded to 0..2^63-1 where appropriate.
Recipe multiplication and cumulative quantities are checked before storing state.

SQLSTATE 40001 and 40P01 trigger a bounded whole-transaction retry. Other errors before
COMMIT are surfaced as aborted attempts. An error after COMMIT is attempted can mean
the result is unknown. The adapter does not invent a definite refusal. It reconciles
using the same operation identity. A missing receipt is NOT_OBSERVED, not proof that
nothing happened; an in-flight transaction may still be unresolved.

The setup revokes PUBLIC schema/table access, but the connection role is a trusted
writer. Neither JSONB nor REVOKE prevents an owner, administrator, migration or other
privileged writer from bypassing the Python reducer. Deployment must close or explicitly
account for every writer before making a database-wide invariant claim. The live harness
checks the interface only and does not qualify arbitrary production permissions.

The operation schema is a protocol boundary. Do not change the meaning of a command
while reusing old operation identities or treating old receipts as new-version execution.
The immutable recipe ID is part of work-order meaning. Code/toolchain/configuration pins
must accompany a deployed instance; the included local file hash is an observation,
not proof of already-loaded runtime identity or trustworthy server administration.

Primary reference material consulted for the design:
- https://www.postgresql.org/docs/current/transaction-iso.html
- https://www.psycopg.org/psycopg3/docs/basic/transactions.html

Those documents describe the external system; they are not evidence that this adapter
has passed a live test. Unit fixtures exercise exact SQL ordering, rollback, retries,
receipt identity and host-failure handling without pretending to be PostgreSQL.


Turn 4 repair: an injected connector must expose `autocommit is False` and an idle
`info.transaction_status` (psycopg IDLE, numeric value zero). Unknown, autocommit or
already active connections refuse before transaction SQL. The factory must provide
fresh, exclusively owned connections, never a borrowed in-flight transaction.
Typed Refusal exceptions after COMMIT is attempted also become unknown outcomes,
unless the driver reports a known transaction-abort SQLSTATE through its normal
exception path. Stored receipts undergo closed-shape, outcome, integer and exact
request validation. Receipt consistency does not authenticate a database administrator.
