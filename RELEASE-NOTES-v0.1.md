# Invariant Workbench v0.1

Invariant Workbench is an experimental, local-first obligation and evidence system.
It binds requirements, restricted operations, scenarios, execution results, and
proof artifacts without silently treating one evidence class as another.

## v0.1 retag disclosure

During the initial public stabilization window, the published `v0.1` tag was
replaced in place to correct clone line-ending verification, add closed-world clone
verification, disclose the Windows constant lane accurately, and add Ubuntu and
Windows CI. This was an explicit same-version replacement, not an assertion that the
two identities contain the same bytes.

- Original public tag target: `7323ee835f4115626fd1d74b5764214721d4b524`
- Original manifest root: `211347a9c33ede16bab2bb7c1f866f6df17414de9befa126eb2b1d0b8d54016d`
- Final `v0.1` tag target: `30009c2920c661347c2366c05b1c98c61b8bc09b`
- Final manifest root: `bb8b73dcc822f309b6c143b594480d6782893666ceff7d24dd70628e7d2d2c15`
- Final archive SHA-256: `f376e3153e25481932023c950424f9f35011755c0dad4c6dd5668221e8ca30d7`

Anyone who fetched the original tag must refresh it explicitly:

```console
git fetch origin tag v0.1 --force
```

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
