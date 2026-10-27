# Turn 4 reconstructed repair candidate

**BUILDER_RECONSTRUCTED_AND_REQUALIFIED. INFORMATION_ONLY. Authority effect NONE.**

This is a new successor to the actually delivered `e3ddaa4b...` archive. It is not
recovery of the unavailable `72f8e68a...` ZIP, and deliberately has a new name/hash.
The two original archives and the exact delivered predecessor remain unchanged.

## Included repairs

1. Both replay helpers refuse source-inventory output before creating anything,
   including `evidence/../...` escapes. New output under evidence/ or outside the
   project remains allowed. Existing and symlink-aliased paths are refused.
2. Windows path-based stat execute bits for .bat/.cmd/.exe/.com are handled narrowly.
   Full same-API metadata equality and cross-API device/inode/size/timestamp equality
   remain required. Other permission differences and file replacements still refuse.

The reconstruction itself reproduced Windows behavior with controlled metadata on
Linux. The later Zucchini-live successor also passed the full regression on a genuine
Windows host, including junction-backed alias tests. This remains no general filesystem
security proof, and native Windows UI acceptance is still a separate open gate.

## Fresh measured results before archive freeze

| Check | Result |
|---|---:|
| Application regression | 373 passed |
| Unchanged native UCM proof methods | 9 passed |
| Additional unchanged UCM manager/migration methods | 38 passed |
| Total distinct methods | **420 passed; zero failures, errors or skips** |
| New reconstruction methods | 33, included in 420 |
| Scalar proof obligations / conditions | 57 / 86; zero residual for correct examples |
| Correct finite examples | 7 passed, separate from proof |
| Defective variants | 7 target-specific failures reproduced separately |
| Lifecycle finite exploration | 54 states, 540 transitions |
| Builder-authored C++ probe | 965 finite cases; not Zucchini or a C++ proof |
| Foundry regeneration | Both generated files replayed |
| Headless UI | 18 projections; no real Windows HWND |
| Vendor / example preservation | All 62 vendor files and 6 original example files unchanged |
| Original seven Turn 3 findings | Reproduced using the repaired helper and pinned original subject |

A test repeated in different campaigns is not counted as a new distinct method.
The 33 new methods include the four missing helper-output cases and 29 additional
metadata/path-boundary regressions. They are reconstruction tests, not the exact
source of the four unrecovered tests from the earlier claimed archive.

## Fresh evidence and source identity

Current proof evidence is regenerated under evidence/qualification/demo. The old
proof dossier is preserved only inside the historical predecessor ZIP. Its identity
is not silently reused for this changed engine. The frontend still is trusted code,
not a formally verified compiler. These claims do not extend to arbitrary Python,
C++, a live database, production writers or physical inventory.

Source root: `f6101e874c9c43e86b574a1b69974d93d7f5d11acf983c0e5a3695345fd9c505`

Core qualification root: `b1e2edb27754f5162e499aaa10eb9cad3e289347ca7f20164d757c5255ea9597`

Measurements here precede final sealing. The exact final ZIP is subsequently
verified and replayed from a fresh extraction. Those transport-bound results are
in the separate external reconstruction receipt, so the archive is not modified
after that final replay to insert a self-referential claim.

## Open gates

Actual Windows replay and native HWND acceptance, live upstream Zucchini, live
PostgreSQL, actual model execution, production custody and independent review remain
open. The user-reported predecessor Windows run was attempted and blocked; it is
not erased by marking this new candidate NOT_RUN. Human maintenance economics are
unmeasured. No release, deployment or Governor authority is created.

## Replay

Extract to a NEW directory, not over an older candidate.

```console
python -I -B ./tools/miw.py verify-dossier --directory ./evidence/qualification/demo
python -I -B ./tools/replay_turn4.py --out ./evidence/my-reconstruction-replay
```

Full regression needs explicitly installed cryptography. Nothing installs itself.
The optional `--include-local-cpp` flag compiles the included finite C++ probe with
an installed compiler. It does not fetch Zucchini or enable a database/model call.
