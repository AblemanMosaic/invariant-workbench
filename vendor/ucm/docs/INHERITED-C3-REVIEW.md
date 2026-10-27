# Independent review: UCL-UCM Agent Workbench c3

**Outcome: INCOMPLETE_REVIEW. The terminal verdict is withheld,** because a required leg is missing.

- Tier 0 is complete and clean.
- Tier 2 is complete and passes on both Python 3.12.3 and 3.13.16.
- Tier 1 (work order items 1–10) was not performed in this session and must go to another reviewer.

I found no MED or higher issue in what I examined. The c2 finding AWB2-03 is **closed**.

Standing remains INFORMATION_ONLY and the authority effect is NONE. This review grants no standing, real A5, G0, admission, installation, release, publication or production.

## Subject

| Item | Value |
|---|---|
| Handoff | `1a32a220…` (matches the stated hash) |
| Transport | `b02fa8de…` |
| Cold archive | `e2aea448…` |
| Source root | `95457400…` (1,795 files) |
| Qualification root | `0d4ae8d4…` |

**Out of scope:** the c4 progress-channel successor. It was given only as Windows paths, so it was not supplied, and it was not reviewed. I found no progress-channel code in c3; every "progress" match in the active tree is lineage code that predates c3.

## Tier 0: complete and clean

**Custody**
- All stated hashes match.
- The handoff, receipt, exact-input, manifest and parsimony roots all recompute.
- The transport is the closed six-member set.

**Verifier**
- `VERIFY.py` passes on 3.12.3 and 3.13.16.
- Import tracing confirms that no subject module is loaded.

**Reconstruction and profiles**
- My own decode gives 1,795 files and `95457400`, twice.
- The four profiles nest strictly (21, 137, 205, 1,795 files).
- Every object is referenced, and no evidence appears in any profile.

**Historical tree**
- `historical/pcb-c3` is byte-identical to my PCB c3 reconstruction (`7e99d115`).
- It appears only in `FULL_DEVELOPMENT`.

**Exact inputs**
- All 22 exact inputs are present at their pins.

**c2 carriage (work order Tier 0 item 4)**
- These carried files are byte-identical to my originals:
  - the c2 handoff (`c804576f`), transport (`f58e40fd`) and freeze receipt;
  - all four of my c2 review files.
- `AWB-C2-INDEPENDENT-REVIEW-DISPOSITION.json` records the c2 outcome as HOLD_FOR_REPAIR.
- It also records Tier 1 as REQUIRED_FOR_C3_INDEPENDENT_REVIEW.

**c2 to c3 change set**
- 31 active files changed and 20 were added; none were removed.
- The changes are the workbench modules, `checkers` and `obligations`, tests, tools, and the new native-proof subsystem and specs.
- Nothing under `historical/`, `predecessors/` or `reviews/` changed.

## Tier 2: complete

I used the same isolated virtualenvs you authorized for c2: `blake3` 1.0.11 and `cryptography` 50.0.2. Nothing new was installed.

| Interpreter | Result | Tests | Qualification root | Deterministic records | Cold archive | Time |
|---|---|---|---|---|---|---|
| CPython 3.12.3 | **PASS** | 1,118 | `0d4ae8d4` | 9 of 9 match | byte-identical | 19 min 42 s |
| CPython 3.13.16 | **PASS** | 1,118 | `0d4ae8d4` | 9 of 9 match | byte-identical | 19 min 15 s |

This matches the builder's claim of 1,118 tests and 9 of 9 artifacts. It is a cross-host reproduction on both declared Python minors. The cold archive rebuilt on each interpreter equals the shipped one.

**AWB2-03 repair: confirmed** (`tier2/AWB2-03-repair-check.json`)

The work order asks to confirm that verifier generation stays byte-identical when `ast.unparse` is unavailable or formats differently.
- `tools/build_workbench_verifier.py` now returns the checked-in `tools/ucm_external_verify.py` bytes.
- It uses `ast` only to parse the source and validate imports and entry points.
- I loaded the builder myself on both interpreters and ran three cases:
  - normal;
  - with `ast.unparse` deleted;
  - with `ast.unparse` replaced by a formatter that changes the output.
- In every case the output equals the shipped `VERIFY.py` (`961f650a`).
- No other `ast.unparse` use remains in the active `src/`, `tools/` or `tests/`.

**Shipped bounded courts** (bounded regression evidence only; not Tier 1)
- I ran the builder's own courts under 3.13 on a disposable copy:
  - native proof court: PASS, 10 tests;
  - c3 repair court: PASS, 25 tests.
- Both bind source root `95457400`.

## Findings

### AWB2-03 (MED in c2): **CLOSED**

The repair matches one of the options proposed in c2 (ship the verifier as source). The qualification now reproduces on 3.12.3, which failed under c2.

### AWB3-01 (INFO): custody, reconstruction and carriage facts all verify

### AWB3-02 (INFO): change scope and naming carry-overs

- The change set is as stated above.
- The replay, freeze and evidence paths still use c1 schema names (`workbench_c1_frozen_replay.v1`, `evidence/workbench-c1/`). This was already noted in c2.
- The carried c2 disposition says Tier 1 "items 1–7". The c3 work order lists items 1–10. Both remain required.

## Dispositions

| Area | Disposition |
|---|---|
| Packaging | PASS (Tier 0; cold archive reproduced on both interpreters) |
| Qualification | PASS on 3.12.3 and 3.13.16 |
| Inherited self-hosting and constitutional computation | PASS (historical tests within the 1,118; historical tree exact) |
| Native proof subsystem | Shipped court and active tests PASS; not attack-tested |
| Staging | Not assessed (Tier 1) |
| Migration | Not assessed (Tier 1) |
| Worker custody | Not assessed (Tier 1) |
| Recovery authorization | Not assessed (Tier 1) |
| Candidate-bound testing | Not assessed (Tier 1) |
| Lane execution | Not assessed (Tier 1) |
| All agent surfaces | Not assessed (Tier 1) |
| Joint composition | Not assessed (Tier 1) |

Windows and protected-host legs are not covered.

## To complete

1. Have another reviewer run Tier 1 items 1–10 against the frozen c3. A terminal verdict is possible only after that.
2. Submit c4 separately, as files, once it has passed full qualification.
