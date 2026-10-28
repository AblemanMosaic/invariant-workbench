# Public-slim package boundary

This is the GitHub-oriented source and runnable-evidence distribution of Invariant
Workbench v0.1. It preserves the application, tests, vendored runtime dependencies,
canonical runnable dossier, integration example, self-contract, verifier, and compact
qualification records.

It intentionally omits:

- embedded Turn 3 and Turn 4 predecessor ZIPs;
- repeated historical demo and qualification generations;
- duplicate Windows/Linux generated dossier copies;
- the two large Zucchini dependency-envelope inventories. Their parent-archive bytes
  and inherited declarations are reconciled in
  `evidence/zucchini-live-acceptance/PUBLIC-SLIM-HASH-AUDIT.json`; one inherited
  declaration is explicitly stale and is not promoted as an exact identity.

Omission is a packaging decision, not evidence destruction. The full custody successor
remains the provenance carrier. This package does not claim to reconstruct omitted
members, and the optional predecessor-defect helper requires the exact separately
preserved Turn 3 archive at its documented path.

The package is closed-world sealed by `MANIFEST.json`. Verify the external archive
with `VERIFY.py ARCHIVE --sha256 SHA256`, or verify a Git checkout with
`VERIFY.py --directory .`. The external public-slim receipt records the full
successor parent identity, deterministic-build comparison, qualification results, and
the boundary-manifest verification.

One replay console record originally contained a builder-host absolute output path.
The public package replaces that record with an explicit non-authoritative redaction
notice while retaining the authoritative replay summary and generated result. This is
a privacy cleanup, not a claim that the original raw console bytes are present.

Invariant Workbench is licensed under Apache License 2.0. Third-party components
retain their separately recorded license and notice terms.
