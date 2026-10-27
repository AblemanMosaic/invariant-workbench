# Retained upstream material and notices

## UCL/UCM c4

The selected unchanged code/doc/test subset is from the user-supplied
UCL-UCM-AGENT-WORKBENCH-c4-INDEPENDENT-REVIEW-HANDOFF.zip, SHA-256
`6bb3d7eb05cfb830d9dbe4253be5326ce67f7b306c6646b94107a321e355cd69`.
Original source and additional closure pins are retained under `vendor/ucm/`.
No UCM release, independent-review closure or production authority is inferred.

## Mosaic UI

The actual user Library archive `mosaic-ui-0.2.0rc1-rich-document-candidate.zip`
has SHA-256 `5bca2ad0f2ed675a056a3a83b3f06af7b2f0049a910cb2c2054c365110c6407d`.
Its retained HEADLESS/WIN32 subset, Foundry and unchanged helper modules are pinned
by `vendor/mosaic/UPSTREAM-PIN.json`. Upstream LICENSE and NOTICE remain included.
Generated slice metadata is distinguished from unchanged original members.
The module's 0.1.0 report and distribution's 0.2.0rc1 name remain distinct observations.

The original Mosaic sun PNG is byte-identical to the asset carried by the supplied
MUVD_BATCH_A_SOURCE.zip (archive SHA-256 `cc3514df610312b3027ec45550ed59c76adf688aadcce68152adab29c9f23dd5`).
Sun SHA-256: `579066ae7b048e5a56bbc99033f2d4316a8c7cdc85e161db9680525ea72639e3`.
No font files are distributed.

## External tools

No upstream Zucchini implementation is vendored or rebuilt by this cleanup. Exact
evidence from the separately accepted pinned Linux build is retained under
`evidence/zucchini-live-acceptance/`; the support-profile fixtures and standalone C++
probe remain explicitly synthetic or builder-authored. PostgreSQL, psycopg,
cryptography, g++, CMake and Ollama remain
separate optional host dependencies as documented. No model weights, compiler binaries,
DB binaries or installed third-party cryptography packages are bundled in this archive.
