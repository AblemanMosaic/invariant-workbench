> Historical builder review retained from the delivered Turn 4 predecessor. Its
> evidence path references refer to that preserved archive, not current qualification.
> Reconstruction findings and new measurements are in RECONSTRUCTION.md and
> ../evidence/RECONSTRUCTION-COMPLETION.md. No independent closure is inferred.

# Turn 4 builder review and consolidated repair

## Identity and disposition

Reviewed predecessor: `Mosaic_Invariant_Workbench_Turn3_CANDIDATE.zip`.
SHA-256: `bedce795797dbb2f170aa293c60fea19f371bc34f41440e1f6ea8eba860b9ef7`.
Review actor: the same assistant acting as builder in this continuation.
**This is not independent review.** The scoped courthouse connection returned a
connection error, so no independent opinion or signer was obtained. No alternate
review identity is invented. Inherited UCM review remains open.

The repair scope is authorized by the user's Turn 4 instruction, not by a test PASS.
The original archive, business contracts/operations, UCM vendor and Mosaic vendor
remain unchanged. One Turn 4 experimental successor carries the repairs.

## Reproduced findings

| ID | Severity in stated scope | Before repair | Consolidated repair |
|---|---|---|---|
| T4-01 | MED | Explicit `status="failed"` without a failure child became PASSED. | Known explicit states are interpreted; unknown/contradictory states and incorrect suite counters refuse. |
| T4-02 | HIGH, custom connector | An injected autocommit connector was accepted although the adapter relies on one transaction. The default psycopg factory already requested autocommit=False. | Require explicit non-autocommit, idle connection metadata before SQL. |
| T4-03 | HIGH, typed connector error | A Refusal raised after fixture commit bypassed OutcomeUnknown classification. The fixture state had already changed. | Every such post-COMMIT typed error preserves outcome uncertainty and same-ID reconciliation. |
| T4-04 | MED, low-level output helper | `write_json` overwrote an existing hard-linked target. The ordinary CLI already refused differing existing output content. | Exclusive creation; explicit internal replacement only; symlink ancestors and linked targets refused. |
| T4-05 | MED | A resealed execution record could contain a failed assertion under a passed scenario, and dossier verification accepted it as a recorded observation. Native arithmetic proofs were not bypassed. | Pure consistency validation; retain mutant execution snapshots; rederive attribution, imports, graph, phase bindings and HTML projection. |
| T4-06 | MED | A resealed request with inconsistent embedded source and an invalid standing passed request review. Output standing still remained information-only. | Reconstruct the complete permitted request and require exact semantic equality before review or model transport. |
| T4-07 | MED | An empty CMake project with no tests/reports returned the runner's successful CLI path. It was an observed local build, not actual Zucchini. | Error on zero tests; require supported reports, matched executions and successful observations for acceptance. |

Each reproduction used disposable local inputs. Database observations here use a
protocol fixture, not a server. The exact observations are in
`evidence/review/TURN3-CHALLENGE-OBSERVATIONS.json`. The preserved probe script is a
historical record; the helper under tools reproduces it against the retained archive.

## Review coverage and limits

R01/R02: inspect the closed AST and native proof path; replay old/new exact proofs,
certificate/subject/residue tamper regressions, nonvacuity witnesses and additional
Boolean-path differential cases. No compiler-correctness theorem is added.
R03/R04/R05: rederive assertion attribution, request semantics and protected edit scope;
exercise malformed/resealed data and output aliases. No OS sandbox is claimed.
R06: replay unchanged manager/migration tests and actual fixture-signed campaign.
No production Governor or external custody is bound.
R07/R08: replay bounded lifecycle, attribution, integer bounds and SQL fault protocols.
No live server or unbounded concurrency theorem is supplied.
R09: exercise actual CMake/CTest fixture plumbing and strict imported data handling.
No complete upstream Zucchini source closure was available during the original Turn 4
review. The later pinned live campaign closed that specific build/report-compatibility
gap for commit `e8595c9ae94e45c1e28a3effeb7555725c3ac741`; see
`evidence/zucchini-live-acceptance/`. This does not rewrite the historical review.
R10/R11/R12: recompile Foundry inputs; run headless/fake-host checks; requalify a recipe
change; verify archive bytes and replay the full local campaign after extraction.
No native Windows witness or independent reviewer is manufactured.

The result supports experimental inspection and local development. It does not
support a production admission or an end-to-end proof for an existing C++ MES.
