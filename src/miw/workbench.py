"""Interactive obligation workspace over MIW's existing evidence classes.

The workbench never upgrades scenario coverage, execution, proof, or a proposed
cross-system binding into another evidence class.  Every projection remains
rooted and carries its claim boundary.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .bdd import run_feature
from .common import BOUNDARY, Refusal, check_seal, digest, read_bytes, read_json, require, root, seal
from .dossier import verify_dossier
from .proofs import verify_source_proof

EVIDENCE_CLASSES = (
    "REQUIREMENT", "IMPLEMENTATION", "SUBJECT_PROOF", "SCENARIO_SPECIFICATION",
    "EXECUTED_EXAMPLES", "ZUCCHINI_DECLARATION", "ZUCCHINI_EXECUTION",
    "COUNTEREXAMPLE", "ASSUMPTION", "EXTERNAL_GATE",
)
LANES = ("INSPECT", "PROOF_RECHECK", "BDD_RERUN", "ZUCCHINI_REVIEW", "CONFORMANCE_WITNESS")
TARGETS = frozenset({"PROOF_RECHECK", "BDD_RERUN", "ZUCCHINI_REVIEW", "CONFORMANCE_WITNESS", "DOSSIER_VERIFY"})


def _requirements(contract: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    def add(identifier: str, kind: str, statement: str) -> None:
        require(type(identifier) is str and identifier.startswith("REQ_"), "WORKBENCH_REQUIREMENT_ID_REFUSED")
        existing = rows.get(identifier)
        if existing is None:
            rows[identifier] = {"id": identifier, "kind": kind, "statement": statement}
        else:
            require(existing["kind"] == kind and existing["statement"] == statement,
                    "WORKBENCH_REQUIREMENT_COLLISION", detail=identifier)
    add(contract["decision_requirement"], "DECISION", contract["accept_when"])
    for state, identifier in contract["state_requirements"].items():
        add(identifier, "STATE_ACCOUNTING", f"Output state {state} follows accepted/refused transition")
    for invariant in contract["invariants"]:
        add(invariant["id"], "INVARIANT", invariant["formula"])
    return [rows[key] for key in sorted(rows)]


def _binding_map(bindings: Mapping[str, Any] | None, requirement_ids: set[str], zucchini_tags: set[str]) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    if bindings is None:
        return [], {}
    require(type(bindings) is dict and bindings.get("schema") == "miw.requirement-binding-set.v1",
            "WORKBENCH_BINDING_SCHEMA_REFUSED")
    require(bindings.get("authority_effect") == "NONE" and bindings.get("standing") in {"PROPOSED", "REVIEWED_LOCAL"},
            "WORKBENCH_BINDING_STANDING_REFUSED")
    rows = bindings.get("bindings")
    require(type(rows) is list, "WORKBENCH_BINDING_ROWS_REFUSED")
    seen = set(); by_requirement: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        require(type(row) is dict and set(row) == {"miw_requirement_id", "zucchini_tag", "relation", "rationale"},
                "WORKBENCH_BINDING_ROW_REFUSED")
        pair = (row["miw_requirement_id"], row["zucchini_tag"])
        require(pair not in seen and pair[0] in requirement_ids and pair[1] in zucchini_tags,
                "WORKBENCH_BINDING_REFERENCE_REFUSED")
        require(row["relation"] in {"CANDIDATE_CORRESPONDENCE", "SUPPORTS_TEST_DESIGN", "EXACT_TAG_MATCH"},
                "WORKBENCH_BINDING_RELATION_REFUSED")
        require(type(row["rationale"]) is str and row["rationale"], "WORKBENCH_BINDING_RATIONALE_REQUIRED")
        seen.add(pair); by_requirement.setdefault(pair[0], []).append(deepcopy(row))
    return deepcopy(rows), by_requirement


def build_workspace(dossier: Path, bindings: Mapping[str, Any] | None = None) -> dict[str, Any]:
    dossier = Path(dossier)
    dossier_check = verify_dossier(dossier)
    summary = read_json(dossier / "SUMMARY.json")
    contract = read_json(dossier / "assembly.contract.json")
    proof = read_json(dossier / "assembly.proof.json")
    execution = read_json(dossier / "assembly.execution.json")
    zucchini = read_json(dossier / "zucchini.execution-link.json")
    requirements = _requirements(contract)
    requirement_ids = {row["id"] for row in requirements}
    zucchini_tags = {row["tag"] for row in zucchini["requirements"]}
    binding_rows, by_requirement = _binding_map(bindings, requirement_ids, zucchini_tags)
    discovery = execution["discovery"]
    covered = set(discovery["requirements"])
    execution_statuses: dict[str, list[str]] = {key: [] for key in requirement_ids}
    for scenario in execution["runs"]:
        for assertion in scenario["assertions"]:
            execution_statuses[assertion["requirement"]].append(assertion["status"])
    mutation_by_target: dict[str, list[dict[str, Any]]] = {}
    for mutation in summary["mutations"]:
        mutation_by_target.setdefault(mutation["target"], []).append(mutation)
    zucchini_by_tag = {row["tag"]: row for row in zucchini["requirements"]}
    obligation_rows = []
    for requirement in requirements:
        identifier = requirement["id"]
        evidence = [
            {"class": "REQUIREMENT", "root": root(contract), "status": "EXACT_SUBJECT",
             "claim_boundary": "Requirement text and identifiers only"},
            {"class": "SUBJECT_PROOF", "root": proof["proof_root"],
             "status": proof["outcome"],
             "claim_boundary": "The complete restricted source/contract subject is checked; this row is not a separately authored requirement-to-VC proof map"},
        ]
        if identifier in covered:
            statuses = execution_statuses[identifier]
            evidence.extend([
                {"class": "SCENARIO_SPECIFICATION", "root": discovery["discovery_root"],
                 "status": "DECLARED_COVERAGE", "claim_boundary": "Coverage is not execution or proof"},
                {"class": "EXECUTED_EXAMPLES", "root": execution["execution_root"],
                 "status": "PASSED" if statuses and all(x == "PASSED" for x in statuses) else "FAILED_OR_INCOMPLETE",
                 "observations": len(statuses), "claim_boundary": "Only recorded concrete examples"},
            ])
        for mutation in mutation_by_target.get(identifier, []):
            evidence.append({"class": "COUNTEREXAMPLE", "root": digest(read_bytes(dossier / f"mutant.{mutation['id']}.counterexample.json")),
                             "status": mutation["counterexample_outcome"], "mutation_id": mutation["id"],
                             "claim_boundary": "A defect-specific executed witness, not an exhaustive disproof"})
        for binding in by_requirement.get(identifier, []):
            zrow = zucchini_by_tag[binding["zucchini_tag"]]
            evidence.extend([
                {"class": "ZUCCHINI_DECLARATION", "root": zucchini["import_root"],
                 "status": "BOUND_" + bindings["standing"], "tag": binding["zucchini_tag"],
                 "relation": binding["relation"], "claim_boundary": "Binding standing is preserved; declarations are not proof"},
                {"class": "ZUCCHINI_EXECUTION", "root": zucchini["link_root"],
                 "status": zrow["execution_status"], "observations": zrow["execution_statuses"],
                 "claim_boundary": zucchini["association"]},
            ])
        obligation_rows.append({**requirement, "evidence": evidence,
                                "evidence_classes": [x["class"] for x in evidence],
                                "proof_projection": "FORMALLY_CHECKED_IN_SUBJECT" if proof["outcome"] == "CHECKED_SOURCE_PROOF" else "OPEN",
                                "scenario_projection": "COVERED" if identifier in covered else "UNCOVERED",
                                "zucchini_projection": "BOUND" if by_requirement.get(identifier) else "UNBOUND"})
    unbound_zucchini = [tag for tag in sorted(zucchini_tags)
                        if not any(row["zucchini_tag"] == tag for row in binding_rows)]
    integrations = [
        {"id": "NATIVE_SCALAR_PROOF", "status": "MEASURED", "evidence_root": proof["proof_root"],
         "scope": "Restricted scalar Python subject"},
        {"id": "BDD_EXECUTION", "status": "MEASURED", "evidence_root": execution["execution_root"],
         "scope": "Bundled concrete examples"},
        {"id": "ZUCCHINI_IMPORT", "status": "MEASURED", "evidence_root": zucchini["link_root"],
         "scope": zucchini["association"]},
        {"id": "POSTGRES_REFERENCE", "status": "DECLARED", "evidence_root": None,
         "scope": "Reference adapter; live acceptance open"},
        {"id": "CPP_CORRESPONDENCE", "status": "DECLARED", "evidence_root": None,
         "scope": "Finite builder probe only; not formal C++ proof"},
        {"id": "MOSAIC_NATIVE_UI", "status": "DECLARED", "evidence_root": None,
         "scope": "Foundry bound; native human acceptance open"},
    ]
    body = {"schema": "miw.invariant-workspace.v1", **BOUNDARY,
            "dossier_manifest_root": dossier_check["manifest_root"],
            "dossier_check_root": dossier_check["dossier_check_root"],
            "subject": {"contract_root": root(contract), "source_sha256": proof["subject"]["source_sha256"],
                        "proof_root": proof["proof_root"], "execution_root": execution["execution_root"],
                        "zucchini_link_root": zucchini["link_root"]},
            "evidence_classes": list(EVIDENCE_CLASSES), "obligations": obligation_rows,
            "bindings": binding_rows, "unbound_zucchini_requirements": unbound_zucchini,
            "integrations": integrations,
            "open_assumptions": ["DATABASE_STATE_MATCHES_PHYSICAL_STOCK", "NO_UNCONTROLLED_WRITER",
                                 "TRANSACTION_ISOLATION_AND_RETRY_MODEL", "SPECIFICATION_MEANING_APPROVED_BY_HUMAN"],
            "claim": "Evidence-class-preserving obligation workspace; no evidence promotion or product correctness claim"}
    return seal(body, "workspace_root")


def propose_binding(workspace: Mapping[str, Any], requirement_id: str, zucchini_tag: str,
                    relation: str, rationale: str) -> dict[str, Any]:
    checked = check_seal(dict(workspace), "workspace_root")
    require(requirement_id in {x["id"] for x in checked["obligations"]}, "WORKBENCH_REQUIREMENT_UNKNOWN")
    known_tags = set(checked["unbound_zucchini_requirements"]) | {x["zucchini_tag"] for x in checked["bindings"]}
    require(zucchini_tag in known_tags, "WORKBENCH_ZUCCHINI_TAG_UNKNOWN")
    require(relation in {"CANDIDATE_CORRESPONDENCE", "SUPPORTS_TEST_DESIGN", "EXACT_TAG_MATCH"},
            "WORKBENCH_BINDING_RELATION_REFUSED")
    require(type(rationale) is str and rationale.strip(), "WORKBENCH_BINDING_RATIONALE_REQUIRED")
    body = {"schema": "miw.requirement-binding-proposal.v1", **BOUNDARY,
            "standing": "PROPOSED", "workspace_root": checked["workspace_root"],
            "miw_requirement_id": requirement_id, "zucchini_tag": zucchini_tag,
            "relation": relation, "rationale": rationale,
            "nonclaim": "Proposal does not establish semantic equivalence, proof, or specification approval"}
    return seal(body, "binding_root")


def select_obligation(workspace: Mapping[str, Any], requirement_id: str, lane: str) -> dict[str, Any]:
    checked = check_seal(dict(workspace), "workspace_root")
    rows = {x["id"]: x for x in checked["obligations"]}
    require(requirement_id in rows, "WORKBENCH_REQUIREMENT_UNKNOWN")
    require(lane in LANES, "WORKBENCH_LANE_UNKNOWN")
    body = {"schema": "miw.obligation-selection.v1", **BOUNDARY,
            "workspace_root": checked["workspace_root"], "requirement_id": requirement_id,
            "lane": lane, "evidence_roots": sorted({x["root"] for x in rows[requirement_id]["evidence"]}),
            "evidence_classes": rows[requirement_id]["evidence_classes"]}
    return seal(body, "selection_root")


def lower_obligation(workspace: Mapping[str, Any], selection: Mapping[str, Any], target: str) -> dict[str, Any]:
    checked = check_seal(dict(workspace), "workspace_root")
    selected = check_seal(dict(selection), "selection_root")
    require(selected["workspace_root"] == checked["workspace_root"], "WORKBENCH_SELECTION_MISMATCH")
    require(target in TARGETS, "WORKBENCH_TARGET_UNKNOWN")
    row = next(x for x in checked["obligations"] if x["id"] == selected["requirement_id"])
    required = {
        "PROOF_RECHECK": "SUBJECT_PROOF", "BDD_RERUN": "SCENARIO_SPECIFICATION",
        "ZUCCHINI_REVIEW": "ZUCCHINI_DECLARATION", "CONFORMANCE_WITNESS": "REQUIREMENT",
        "DOSSIER_VERIFY": "REQUIREMENT",
    }[target]
    available = required in row["evidence_classes"]
    result = "BOUNDED" if available and target not in {"CONFORMANCE_WITNESS", "DOSSIER_VERIFY"} else "EXACT" if available else "REFUSED"
    code = None if available else "WORKBENCH_REQUIRED_EVIDENCE_ABSENT"
    body = {"schema": "miw.obligation-lowering.v1", **BOUNDARY,
            "workspace_root": checked["workspace_root"], "selection_root": selected["selection_root"],
            "requirement_id": selected["requirement_id"], "target": target, "result": result,
            "required_evidence_class": required, "refusal_code": code,
            "claim_boundary": {
                "PROOF_RECHECK": "Rechecks the whole restricted proof subject, not a separately compiled requirement theorem",
                "BDD_RERUN": "Runs bounded examples only",
                "ZUCCHINI_REVIEW": "Inspects bound declarations and linked test observations only",
                "CONFORMANCE_WITNESS": "Exports an evidence projection without granting conformance",
                "DOSSIER_VERIFY": "Verifies exact dossier consistency and rederives proof checks",
            }[target]}
    return seal(body, "lowering_root")


def execute_local(lowering: Mapping[str, Any], dossier: Path, *, allow_local_check: bool = False,
                  verified_workspace: Mapping[str, Any] | None = None) -> dict[str, Any]:
    plan = check_seal(dict(lowering), "lowering_root")
    require(allow_local_check, "WORKBENCH_LOCAL_EXECUTION_NOT_AUTHORIZED")
    require(plan["result"] != "REFUSED", plan.get("refusal_code") or "WORKBENCH_LOWERING_REFUSED")
    require(plan["target"] in {"PROOF_RECHECK", "BDD_RERUN", "DOSSIER_VERIFY"},
            "WORKBENCH_TARGET_NOT_LOCALLY_EXECUTABLE")
    dossier = Path(dossier)
    workspace = (check_seal(dict(verified_workspace), "workspace_root")
                 if verified_workspace is not None else build_workspace(dossier))
    require(workspace["workspace_root"] == plan["workspace_root"], "WORKBENCH_RUNTIME_SUBJECT_DRIFT")
    if plan["target"] == "PROOF_RECHECK":
        result = verify_source_proof(read_json(dossier / "assembly.contract.json"),
                                     read_bytes(dossier / "assembly.source.py").decode("utf-8"),
                                     read_json(dossier / "assembly.proof.json"))
        outcome, evidence_root = result["outcome"], result["check_root"]
    elif plan["target"] == "BDD_RERUN":
        result = run_feature(read_json(dossier / "assembly.contract.json"),
                             read_bytes(dossier / "assembly.source.py").decode("utf-8"),
                             read_bytes(dossier / "assembly.feature").decode("utf-8"))
        outcome = "PASSED" if all(x["status"] == "PASSED" for x in result["runs"]) else "FAILED"
        evidence_root = result["execution_root"]
    else:
        result = verify_dossier(dossier); outcome, evidence_root = "PASSED", result["dossier_check_root"]
    return seal({"schema": "miw.workbench-local-execution.v1", **BOUNDARY,
                 "lowering_root": plan["lowering_root"], "target": plan["target"],
                 "outcome": outcome, "evidence_root": evidence_root,
                 "result": result, "external_effect": "NONE"}, "execution_receipt_root")


def compare_workspaces(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    a, b = check_seal(dict(left), "workspace_root"), check_seal(dict(right), "workspace_root")
    keys = ("contract_root", "source_sha256", "proof_root", "execution_root", "zucchini_link_root")
    subject_changes = [{"field": key, "left": a["subject"][key], "right": b["subject"][key]}
                       for key in keys if a["subject"][key] != b["subject"][key]]
    left_rows, right_rows = {x["id"]: x for x in a["obligations"]}, {x["id"]: x for x in b["obligations"]}
    obligation_changes = []
    for identifier in sorted(set(left_rows) | set(right_rows)):
        if left_rows.get(identifier) != right_rows.get(identifier):
            obligation_changes.append({"requirement_id": identifier,
                                       "left": left_rows.get(identifier), "right": right_rows.get(identifier)})
    return seal({"schema": "miw.workspace-comparison.v1", **BOUNDARY,
                 "left_workspace_root": a["workspace_root"], "right_workspace_root": b["workspace_root"],
                 "subject_changes": subject_changes, "obligation_changes": obligation_changes,
                 "same": not subject_changes and not obligation_changes,
                 "claim": "Exact workspace comparison; no semantic equivalence inferred"}, "comparison_root")


def explain_obligation(workspace: Mapping[str, Any], requirement_id: str) -> dict[str, Any]:
    checked = check_seal(dict(workspace), "workspace_root")
    rows = {x["id"]: x for x in checked["obligations"]}
    require(requirement_id in rows, "WORKBENCH_REQUIREMENT_UNKNOWN")
    row = rows[requirement_id]
    return seal({"schema": "miw.obligation-explanation.v1", **BOUNDARY,
                 "workspace_root": checked["workspace_root"], "requirement": row,
                 "why": [
                     "The requirement is retained as its own evidence class.",
                     "The checked proof is attached at subject scope unless an explicit requirement-to-VC map exists.",
                     "Scenario coverage and executions remain observations, not proof.",
                     "Zucchini evidence appears only through an explicit binding with preserved standing.",
                 ],
                 "open_assumptions": checked["open_assumptions"]}, "explanation_root")
