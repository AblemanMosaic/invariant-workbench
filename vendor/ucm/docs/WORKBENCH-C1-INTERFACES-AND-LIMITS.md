# Supported workbench interfaces and limits

Current successor note: this path is retained from c1, but its interface count
and operational statements below describe c3. The exact c3 surface groups are
listed in `docs/WORKBENCH-C3-AGENT-INTERFACES.md`.

`python -I -B tools/ucm.py discover` returns the 20-surface capability registry. `inspect-source` returns the current staged source root. `project PATH --expected-source-root ROOT` inspects a project only against a caller-held source pin. `verify ARCHIVE --expected-archive-sha256 PIN` checks a cold archive. `stage` forwards exact pinned stage/recover/rollback operations. `qualify --lane FAST|INCREMENTAL|QUALIFICATION` requires the FULL_DEVELOPMENT profile and records the chosen lane; only QUALIFICATION can support the frozen recommendation. The Python `uclop.workbench.Workbench` interface takes an externally checked orientation context, graph, implementation root, manager and bounded worker. Calls carry exact request schemas, a context root, idempotency key and expected journal head.

Staging and rollback receipts report their actual local filesystem `effect_scope` separately from `authority_effect: NONE`. The stage tool may write only within the caller-selected disposable destination and transaction journal. Those receipts do not grant standing, install authority, A5, or G0.

Charter issuance, principal proof and registry seating need distinct signer roles and externally held pins. Local DKN identity derivation uses the imported v1.0 codex. THR correspondence keeps native hash roles distinct. Neither adapter provides a production signer, live UGK admissibility verdict or governed DKN federation. Full development retains the predecessor and its tools as reference material. The other three profiles contain only their declared supported surfaces.

The manager durably records task and successor-plan events through the protected state store. Recovery depends on the caller retaining the latest external head; ambiguous worker effects require reconciliation. Bounded workers can inspect exact source, run explicitly trusted local tests or prepare a fresh candidate tree. Hostile candidate code needs an external OS sandbox. Local files and subprocesses are real effects, while constitutional authority remains NONE. The input PI/APM overlays retain their source semantics: a graph declared without complete edges cannot narrow qualification, and simulated project receipts do not close live obligations.

Portable cold boot means byte-complete staging of a declared profile into a destination with recovery and rollback receipts. It does not install UCM on a target, bind MosaiCOS/Genesis artifacts, create accounts, activate network services, admit a subject or open G0. The MosaiCOS cold-boot interface remains an exact-artifact contract with unfilled target pins.
