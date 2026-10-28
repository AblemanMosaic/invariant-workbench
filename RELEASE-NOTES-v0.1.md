# Invariant Workbench v0.1

Invariant Workbench is an experimental, local-first obligation and evidence system.
It binds requirements, restricted operations, scenarios, execution results, and
proof artifacts without silently treating one evidence class as another.

## Included

- a self-contract and machine-readable `explain` surface;
- constitutional test courts and an agent capability/effect registry;
- a headless semantic application runner and a Windows native viewer lane;
- exact-byte dossier verification and deterministic archive sealing;
- bounded Zucchini report integration with retained pinned-live acceptance evidence;
- assembly and work-order reference models, proof checking, and PostgreSQL adapter
  boundaries;
- public qualification, integration, provenance, and known-limit records.

## Important boundaries

This release does not prove physical inventory, external system truth, every database
writer, production authorization, arbitrary C++ correctness, or correctness of an
unspecified application. Native Windows UI acceptance, live PostgreSQL acceptance,
consumer-owned Zucchini integration, and independent review remain separately named
lanes.

The archive deliberately omits embedded predecessor ZIP files and redundant historical
evidence. Their identities and the omission boundary remain recorded.

## Verify

Verify the published ZIP from a clone or extracted verifier using the SHA-256 sidecar:

```console
python -I -B ./VERIFY.py ./Invariant_Workbench_v0.1.zip --sha256 <SHA256-FROM-SIDECAR>
```

Verify an ordinary Git clone directly against `MANIFEST.json`:

```console
python -I -B ./VERIFY.py --directory .
```

After extracting the verified ZIP into a new directory, run:

```console
python -I -B ./tools/miw.py verify-dossier --directory ./evidence/qualification/demo
python -I -B ./tools/miw.py self-contract-check --out ../iw-self-contract.json
```

## License

Invariant Workbench is licensed under Apache License 2.0. Bundled third-party
components retain their own licenses and notices; see `THIRD-PARTY-NOTICES.md`.
