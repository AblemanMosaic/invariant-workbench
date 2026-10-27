# MIW self-contract and explain surface

Status: `LOCAL_ENGINEERING_CANDIDATE`; `INFORMATION_ONLY`; authority effect `NONE`.

The Invariant Workbench now explicates its own bounded guarantees in
`constitutional/SELF-CONTRACT.json`. This is a machine-checked contract, not a
marketing summary. Each guarantee must name:

- its exact claim and scope;
- the implementation paths that enforce it;
- the CTR courts and builder tests that exercise it;
- the evidence schemas that can carry its results;
- the events that invalidate it;
- the nonclaims that prevent overstatement; and
- the trusted assumptions on which it still depends.

The checker also requires every declared court, nonclaim, and trusted assumption to
be referenced. It verifies that each enforcement path exists and that both public
self-contract operations are classified in the closed operation registry.

## Use it

```console
python -I -B ./tools/miw.py self-contract-check --out ./evidence/self-contract-check.json
python -I -B ./tools/miw.py explain --out ./evidence/self-contract-index.json
python -I -B ./tools/miw.py explain --id G-EXACT-SUBJECT-BOUNDARY
python -I -B ./tools/miw.py explain --id NC-PHYSICAL-INVENTORY
python -I -B ./tools/miw.py explain --id A-HUMAN-SEMANTIC-APPROVAL
```

`explain` accepts a guarantee, nonclaim, or trusted-assumption ID. With no ID it
returns the complete index. Its output is canonical sealed JSON and therefore can be
pinned, compared, and carried into a review dossier.

## What self-hosting means here

MIW uses its own normal disciplines on itself: exact roots, typed evidence,
fail-closed validation, registry closure, CTR coverage, zero-authority explanations,
and requalification after source changes. CTR-09 executes the same checker during
the constitutional campaign. The archive manifest and external archive hash then bind
the checked implementation and contract into the delivered candidate.

This is bounded self-application, not logical self-certification. The contract cannot
prove that its requirements are desirable, that its implementation has no defect, or
that its own checker is trustworthy merely because the checker says so. Python, the
host OS/filesystem, canonicalization and SHA-256, the restricted proof translator and
checker, external archive verification, and human semantic approval remain an
explicit trusted base. Independent review and production admission remain external.

The practical guarantee is narrower and useful: a consumer can ask what MIW claims,
locate the named enforcement and evidence, see exactly what would invalidate the
claim, and inspect the boundary MIW refuses to cross. Nothing becomes authoritative
because MIW explained it.
