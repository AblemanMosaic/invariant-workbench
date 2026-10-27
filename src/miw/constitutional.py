"""Local constitutional control surfaces for the Invariant Workbench.

These are consumer-owned CGP-shaped engineering realizations.  They preserve
claim boundaries and do not claim UGK admission, law, or production authority.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from uclop.canonical import canonical_bytes, root

from .common import BOUNDARY, check_seal, read_json, require, seal


OBSERVABILITY_LEVELS = ("SENTINEL", "RECEIPT", "DIAGNOSTIC")
CGP_VERDICTS = ("PROVEN", "FAIL", "GAP", "WAIVED", "BY-CONSTRUCTION", "NOT-RUN", "ERROR")
EFFECT_CLASSES = (
    "NONE", "CREATE_ONLY_EVIDENCE", "LOCAL_UI", "LOOPBACK_REQUEST",
    "TRUSTED_LOCAL_PROCESS", "DISPOSABLE_DATABASE", "COMPILER_EXECUTION",
)
ADMISSIONS = ("READ_ONLY", "EXPLICIT_OUTPUT", "EXPLICIT_OPT_IN", "EXTERNAL_GATE")


def _unique(rows: Sequence[Mapping[str, Any]], key: str, code: str) -> None:
    values = [row.get(key) for row in rows]
    require(all(type(value) is str and value for value in values), code)
    require(len(values) == len(set(values)), code)


def validate_operation_registry(registry: Mapping[str, Any], *, cli_operations: Sequence[str] = (),
                                ui_operations: Sequence[str] = ()) -> dict[str, Any]:
    require(type(registry) is dict, "CONTROL_REGISTRY_OBJECT_REQUIRED")
    require(registry.get("schema") == "miw.operation-registry.v1", "CONTROL_REGISTRY_SCHEMA_UNSUPPORTED")
    operations = registry.get("operations")
    capabilities = registry.get("capabilities")
    require(type(operations) is list and operations, "CONTROL_OPERATIONS_REQUIRED")
    require(type(capabilities) is list and capabilities, "CONTROL_CAPABILITIES_REQUIRED")
    _unique(operations, "operation_id", "CONTROL_OPERATION_ID_COLLISION")
    _unique(capabilities, "capability_id", "CONTROL_CAPABILITY_ID_COLLISION")
    capability_ids = {row["capability_id"] for row in capabilities}
    operation_ids = {row["operation_id"] for row in operations}
    for index, operation in enumerate(operations):
        path = f"$.operations[{index}]"
        require(operation.get("surface") in {"CLI", "MOSAIC_UI", "AGENT"}, "CONTROL_SURFACE_INVALID", path=path)
        require(operation.get("effect_class") in EFFECT_CLASSES, "CONTROL_EFFECT_CLASS_INVALID", path=path)
        require(operation.get("admission") in ADMISSIONS, "CONTROL_ADMISSION_INVALID", path=path)
        require(operation.get("capability_id") in capability_ids, "CONTROL_CAPABILITY_UNDECLARED", path=path)
        require(type(operation.get("meaning")) is str and operation["meaning"], "CONTROL_MEANING_REQUIRED", path=path)
        require(type(operation.get("claim_ceiling")) is str and operation["claim_ceiling"],
                "CONTROL_CLAIM_CEILING_REQUIRED", path=path)
        if operation["effect_class"] in {"LOOPBACK_REQUEST", "TRUSTED_LOCAL_PROCESS", "DISPOSABLE_DATABASE", "COMPILER_EXECUTION"}:
            require(operation["admission"] in {"EXPLICIT_OPT_IN", "EXTERNAL_GATE"},
                    "CONTROL_EXTERNAL_EFFECT_MUST_BE_EXPLICIT", path=path)
    missing_cli = sorted(set(cli_operations) - operation_ids)
    missing_ui = sorted(set(ui_operations) - operation_ids)
    require(not missing_cli, "CONTROL_CLI_OPERATION_UNCLASSIFIED", detail=",".join(missing_cli))
    require(not missing_ui, "CONTROL_UI_OPERATION_UNCLASSIFIED", detail=",".join(missing_ui))
    body = {
        "schema": "miw.operation-registry-check.v1", **BOUNDARY,
        "registry_root": root(registry), "operations": len(operations),
        "capabilities": len(capabilities), "cli_operations_checked": len(cli_operations),
        "ui_operations_checked": len(ui_operations), "status": "PASSED",
    }
    return seal(body, "check_root")


def compile_operation(registry: Mapping[str, Any], operation_id: str, *,
                      subject: Mapping[str, Any], inputs: Mapping[str, Any],
                      requester: str = "LOCAL_OPERATOR") -> dict[str, Any]:
    validate_operation_registry(registry)
    matches = [row for row in registry["operations"] if row["operation_id"] == operation_id]
    require(len(matches) == 1, "CONTROL_OPERATION_UNDECLARED", detail=operation_id)
    operation = matches[0]
    require(type(subject) is dict and type(inputs) is dict, "CONTROL_PLAN_INPUT_INVALID")
    commitments = {
        "h_s": root({"subject": subject, "inputs": inputs}),
        "h_c": root({"admission": operation["admission"], "effect_class": operation["effect_class"]}),
        "h_m": root({"operation_id": operation_id, "meaning": operation["meaning"],
                     "claim_ceiling": operation["claim_ceiling"]}),
        "h_j": root({"surface": operation["surface"], "requester": requester,
                     "jurisdiction": operation.get("jurisdiction", "LOCAL_WORKBENCH")}),
        "h_r": root({"receipt_schema": operation["receipt_schema"],
                     "terminal_outcomes": operation["terminal_outcomes"]}),
    }
    require(len(set(commitments.values())) == len(commitments), "CONTROL_COMMITMENTS_COLLAPSED")
    return seal({
        "schema": "miw.compiled-operation-plan.v1", **BOUNDARY,
        "operation_id": operation_id, "capability_id": operation["capability_id"],
        "effect_class": operation["effect_class"], "admission": operation["admission"],
        "requester": requester, "commitments": commitments,
        "inputs": dict(inputs), "subject": dict(subject),
        "execution_authority": "NOT_GRANTED_BY_PLAN",
    }, "plan_root")


def capability_surface(registry: Mapping[str, Any]) -> dict[str, Any]:
    check = validate_operation_registry(registry)
    by_capability: dict[str, list[dict[str, Any]]] = {row["capability_id"]: [] for row in registry["capabilities"]}
    for operation in registry["operations"]:
        by_capability[operation["capability_id"]].append({
            "operation_id": operation["operation_id"], "surface": operation["surface"],
            "effect_class": operation["effect_class"], "admission": operation["admission"],
            "claim_ceiling": operation["claim_ceiling"],
        })
    capabilities = []
    for capability in registry["capabilities"]:
        capabilities.append({**capability, "operations": sorted(
            by_capability[capability["capability_id"]], key=lambda row: row["operation_id"]
        )})
    return seal({
        "schema": "miw.agent-capability-surface.v1", **BOUNDARY,
        "registry_root": check["registry_root"], "capabilities": capabilities,
        "observability_levels": list(OBSERVABILITY_LEVELS),
        "mutation_authority": "NONE",
        "claim_ceiling": "Operation discovery and plan compilation only; execution needs each operation's separate admission.",
    }, "surface_root")


def _receipt_status(receipt: Mapping[str, Any] | None, expected: str | None = None) -> str:
    if receipt is None:
        return "GAP"
    try:
        checked = check_seal(dict(receipt), "execution_receipt_root")
    except Exception:
        return "FAIL"
    if expected is not None and checked.get("outcome") != expected:
        return "FAIL"
    return "PROVEN"


def cgp_posture(registry: Mapping[str, Any], workspace: Mapping[str, Any] | None = None,
                proof_receipt: Mapping[str, Any] | None = None,
                bdd_receipt: Mapping[str, Any] | None = None,
                headless_receipt: Mapping[str, Any] | None = None) -> dict[str, Any]:
    registry_check = validate_operation_registry(registry)
    workspace_status = "GAP"
    zucchini_status = "NOT-RUN"
    open_assumptions: list[str] = []
    workspace_root = None
    if workspace is not None:
        try:
            checked = check_seal(dict(workspace), "workspace_root")
            workspace_root = checked["workspace_root"]
            workspace_status = "PROVEN"
            zucchini_status = "PROVEN" if any(row.get("zucchini_projection") == "BOUND" for row in checked["obligations"]) else "GAP"
            open_assumptions = list(checked.get("open_assumptions", []))
        except Exception:
            workspace_status = "FAIL"
    headless_status = "GAP"
    if headless_receipt is not None:
        try:
            checked_headless = check_seal(dict(headless_receipt), "court_root")
            headless_status = "PROVEN" if checked_headless.get("status") == "PASSED_HEADLESS_APPLICATION_COURT" else "FAIL"
        except Exception:
            headless_status = "FAIL"
    axes = {
        "ESA": {"status": workspace_status, "meaning": "Exact local roots and known gaps are legible."},
        "EVS": {"status": "PROVEN" if _receipt_status(proof_receipt, "CHECKED_SOURCE_PROOF") == "PROVEN" and _receipt_status(bdd_receipt, "PASSED") == "PROVEN" else "GAP",
                "meaning": "Supplied proof and example receipts revalidate as their own evidence classes."},
        "COP": {"status": headless_status, "meaning": "Sentinel, Receipt, and Diagnostic projections are available without authority."},
        "SRSA": {"status": "GAP" if open_assumptions else workspace_status,
                 "meaning": "Reliance remains defeasible while named assumptions or external gates are open."},
    }
    body = {
        "schema": "miw.cgp-posture.v1", **BOUNDARY,
        "registry_check_root": registry_check["check_root"], "workspace_root": workspace_root,
        "axes": axes, "zucchini_correspondence": zucchini_status,
        "open_assumptions": open_assumptions,
        "observability": {
            "SENTINEL": "Current bounded status and blockers",
            "RECEIPT": "Rooted consequential operation outcomes",
            "DIAGNOSTIC": "Bounded explanatory detail; no fresh external contact",
        },
        "native_ugk_runtime": "NOT_INVOKED",
        "evs_cop_realization": "MIW_CONSUMER_OWNED_LOCAL_CANDIDATE",
        "claim_ceiling": "Derived local posture only; no authority, semantic approval, external truth, or production admission.",
    }
    return seal(body, "posture_root")


def diagnose(posture: Mapping[str, Any]) -> dict[str, Any]:
    checked = check_seal(dict(posture), "posture_root")
    actions = []
    for axis, row in checked["axes"].items():
        if row["status"] in {"GAP", "FAIL", "ERROR", "NOT-RUN"}:
            actions.append({
                "axis": axis, "status": row["status"],
                "suggested_operation": {
                    "ESA": "workbench-open", "EVS": "workbench-run",
                    "COP": "headless-application", "SRSA": "workbench-explain",
                }[axis],
                "automatic_execution": False,
            })
    health = "HEALTHY_FOR_LOCAL_SCOPE" if not actions else "BOUNDED_GAPS_PRESENT"
    return seal({
        "schema": "miw.repair-debug-diagnostic.v1", **BOUNDARY,
        "posture_root": checked["posture_root"], "health": health,
        "actions": actions, "repair_effect": "NONE",
        "claim_ceiling": "Suggestions only. No source edit, evidence deletion, external call, or governed mutation is authorized.",
    }, "diagnostic_root")


def run_ctr(plan: Mapping[str, Any], registry: Mapping[str, Any], project: Path,
            dossier: Path, bindings: Path | None = None) -> dict[str, Any]:
    """Run the finite local constitutional court catalog."""
    from .cli import parser
    from .foundry_view import payload
    from .headless_runner import application_court
    from .realization_space import validate_bundle
    from .self_contract import validate_self_contract
    from .workbench import build_workspace

    require(plan.get("schema") == "miw.ctr-plan.v1", "CTR_PLAN_SCHEMA_UNSUPPORTED")
    courts = plan.get("courts")
    require(type(courts) is list and courts, "CTR_COURTS_REQUIRED")
    _unique(courts, "court_id", "CTR_COURT_ID_COLLISION")
    expected = {
        "CTR-01-REGISTRY-CLOSURE", "CTR-02-COMMITMENT-SEPARATION",
        "CTR-03-OBSERVABILITY-LEVELS", "CTR-04-RSC-BUNDLE",
        "CTR-05-OBLIGATION-LEDGER", "CTR-06-HEADLESS-APPLICATION",
        "CTR-07-EXTERNAL-EFFECT-ADMISSION", "CTR-08-ZUCCHINI-NONPROMOTION",
        "CTR-09-SELF-EXPLICATION",
    }
    require({row["court_id"] for row in courts} == expected, "CTR_COURT_SET_MISMATCH")
    project = Path(project)
    dossier = Path(dossier)
    subcommands = parser()._subparsers._group_actions[0].choices.keys()
    ui_operations = payload()["application"]["declared_operation_ids"]
    results = []

    def record(court_id: str, function) -> None:
        try:
            evidence = function()
            results.append({"court_id": court_id, "outcome": "PASSED", "evidence_root": root(evidence)})
        except Exception as exc:
            results.append({"court_id": court_id, "outcome": "FAILED",
                            "error_type": type(exc).__name__, "detail": str(exc)[:500]})

    record("CTR-01-REGISTRY-CLOSURE", lambda: validate_operation_registry(
        registry, cli_operations=list(subcommands), ui_operations=ui_operations))
    record("CTR-02-COMMITMENT-SEPARATION", lambda: compile_operation(
        registry, "workbench-open", subject={"dossier": str(dossier)}, inputs={}, requester="CTR"))
    record("CTR-03-OBSERVABILITY-LEVELS", lambda: (
        require(OBSERVABILITY_LEVELS == ("SENTINEL", "RECEIPT", "DIAGNOSTIC"), "CTR_OBSERVABILITY_LEVEL_DRIFT") or
        {"levels": list(OBSERVABILITY_LEVELS)}))
    record("CTR-04-RSC-BUNDLE", lambda: validate_bundle(
        project / "schemas/INVARIANT-EVIDENCE-SPACE-CONTRACT.json",
        project / "schemas/INVARIANT-WORKBENCH-REALIZER-REGISTRY.json",
        project / "schemas/INVARIANT-WORKBENCH-CAPABILITY-DICTIONARY.json"))
    record("CTR-05-OBLIGATION-LEDGER", lambda: build_workspace(
        dossier, read_json(Path(bindings)) if bindings is not None else None))
    record("CTR-06-HEADLESS-APPLICATION", lambda: application_court(dossier, bindings))
    record("CTR-07-EXTERNAL-EFFECT-ADMISSION", lambda: {
        "external": [row["operation_id"] for row in registry["operations"]
                     if row["effect_class"] in {"LOOPBACK_REQUEST", "TRUSTED_LOCAL_PROCESS", "DISPOSABLE_DATABASE", "COMPILER_EXECUTION"}
                     and row["admission"] in {"EXPLICIT_OPT_IN", "EXTERNAL_GATE"}]})

    def nonpromotion() -> dict[str, Any]:
        workspace = build_workspace(dossier, read_json(Path(bindings)) if bindings is not None else None)
        bound = [row for row in workspace["obligations"] if row.get("zucchini_projection") == "BOUND"]
        require(bound, "CTR_ZUCCHINI_BINDING_REQUIRED")
        for obligation in bound:
            evidence = [item for item in obligation["evidence"] if item["class"] == "ZUCCHINI_DECLARATION"]
            require(evidence and all(item["status"] == "BOUND_PROPOSED" for item in evidence),
                    "CTR_ZUCCHINI_BINDING_PROMOTED")
        return {"workspace_root": workspace["workspace_root"], "bound": len(bound)}

    record("CTR-08-ZUCCHINI-NONPROMOTION", nonpromotion)
    record("CTR-09-SELF-EXPLICATION", lambda: validate_self_contract(
        read_json(project / "constitutional/SELF-CONTRACT.json"), project, registry, plan
    ))
    passed = all(row["outcome"] == "PASSED" for row in results)
    return seal({
        "schema": "miw.ctr-report.v1", **BOUNDARY,
        "status": "PASSED" if passed else "FAILED", "plan_root": root(plan),
        "registry_root": root(registry), "courts_run": len(results), "results": results,
        "coverage": {"declared": len(courts), "passed": sum(row["outcome"] == "PASSED" for row in results)},
        "review_class": "BUILDER_AUTHORED_CONSTITUTIONAL_COURTS_NOT_INDEPENDENT_REVIEW",
    }, "ctr_root")


__all__ = [
    "ADMISSIONS", "CGP_VERDICTS", "EFFECT_CLASSES", "OBSERVABILITY_LEVELS",
    "capability_surface", "cgp_posture", "compile_operation", "diagnose",
    "run_ctr", "validate_operation_registry",
]
