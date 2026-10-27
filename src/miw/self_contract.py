"""Sealed self-description for the Invariant Workbench.

The self-contract makes local guarantees, nonclaims, trusted assumptions, code
bindings, courts, evidence schemas, and invalidation rules addressable.  It is
not a recursive proof of MIW, independent review, or production admission.
"""
from __future__ import annotations

import ast
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from uclop.canonical import root

from .common import BOUNDARY, check_seal, require, seal


CONTRACT_KEYS = {
    "schema", "standing", "authority_effect", "product", "version",
    "guarantees", "nonclaims", "trusted_assumptions", "claim_ceiling",
    "self_contract_root",
}
GUARANTEE_KEYS = {
    "guarantee_id", "title", "claim", "scope", "enforcing_paths",
    "court_ids", "test_ids", "evidence_schemas", "invalidated_by",
    "nonclaim_ids", "assumption_ids",
}
NONCLAIM_KEYS = {"nonclaim_id", "statement", "reason"}
ASSUMPTION_KEYS = {"assumption_id", "statement", "failure_effect", "control"}


def _text(value: Any, code: str, *, path: str = "$") -> str:
    require(type(value) is str and bool(value.strip()), code, path=path)
    return value


def _texts(value: Any, code: str, *, path: str) -> list[str]:
    require(type(value) is list and bool(value), code, path=path)
    require(all(type(item) is str and bool(item.strip()) for item in value), code, path=path)
    require(len(value) == len(set(value)), code, path=path)
    return list(value)


def _unique(rows: Sequence[Mapping[str, Any]], key: str, code: str) -> set[str]:
    values = [_text(row.get(key), code) for row in rows]
    require(len(values) == len(set(values)), code)
    return set(values)


def _code_path(project: Path, value: str, *, path: str) -> None:
    require("\\" not in value and ":" not in value, "SELF_CONTRACT_CODE_PATH_INVALID", path=path)
    relative = PurePosixPath(value)
    require(not relative.is_absolute() and all(part not in {"", ".", ".."} for part in relative.parts),
            "SELF_CONTRACT_CODE_PATH_INVALID", path=path)
    candidate = project.joinpath(*relative.parts)
    require(candidate.is_file(), "SELF_CONTRACT_CODE_PATH_MISSING", path=path, detail=value)


def _declared_test_ids(project: Path) -> set[str]:
    tests = project / "tests"
    require(tests.is_dir(), "SELF_CONTRACT_TEST_DIRECTORY_MISSING")
    names: set[str] = set()
    for source_path in sorted(tests.glob("test_*.py"), key=lambda value: value.name):
        try:
            tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=source_path.name)
        except (OSError, UnicodeError, SyntaxError) as exc:
            require(False, "SELF_CONTRACT_TEST_INVENTORY_INVALID", detail=type(exc).__name__)
        names.update(node.name for node in ast.walk(tree)
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and node.name.startswith("test_"))
    require(names, "SELF_CONTRACT_TEST_INVENTORY_EMPTY")
    return names


def validate_self_contract(contract: Mapping[str, Any], project: Path,
                           registry: Mapping[str, Any], plan: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the sealed contract and its live code/court references."""
    require(type(contract) is dict, "SELF_CONTRACT_OBJECT_REQUIRED")
    checked = check_seal(dict(contract), "self_contract_root")
    require(set(checked) == CONTRACT_KEYS, "SELF_CONTRACT_SHAPE_INVALID")
    require(checked["schema"] == "miw.self-contract.v1", "SELF_CONTRACT_SCHEMA_UNSUPPORTED")
    require(checked["standing"] == "LOCAL_ENGINEERING_CANDIDATE", "SELF_CONTRACT_STANDING_INVALID")
    require(checked["authority_effect"] == "NONE", "SELF_CONTRACT_AUTHORITY_INVALID")
    _text(checked["product"], "SELF_CONTRACT_PRODUCT_REQUIRED")
    _text(checked["version"], "SELF_CONTRACT_VERSION_REQUIRED")
    _text(checked["claim_ceiling"], "SELF_CONTRACT_CLAIM_CEILING_REQUIRED")

    guarantees = checked["guarantees"]
    nonclaims = checked["nonclaims"]
    assumptions = checked["trusted_assumptions"]
    require(type(guarantees) is list and guarantees, "SELF_CONTRACT_GUARANTEES_REQUIRED")
    require(type(nonclaims) is list and nonclaims, "SELF_CONTRACT_NONCLAIMS_REQUIRED")
    require(type(assumptions) is list and assumptions, "SELF_CONTRACT_ASSUMPTIONS_REQUIRED")
    guarantee_ids = _unique(guarantees, "guarantee_id", "SELF_CONTRACT_GUARANTEE_ID_INVALID")
    nonclaim_ids = _unique(nonclaims, "nonclaim_id", "SELF_CONTRACT_NONCLAIM_ID_INVALID")
    assumption_ids = _unique(assumptions, "assumption_id", "SELF_CONTRACT_ASSUMPTION_ID_INVALID")
    require(not (guarantee_ids & nonclaim_ids or guarantee_ids & assumption_ids or nonclaim_ids & assumption_ids),
            "SELF_CONTRACT_ID_COLLISION")

    plan_courts = plan.get("courts")
    require(plan.get("schema") == "miw.ctr-plan.v1" and type(plan_courts) is list,
            "SELF_CONTRACT_CTR_PLAN_INVALID")
    court_ids = _unique(plan_courts, "court_id", "SELF_CONTRACT_CTR_ID_INVALID")
    require(registry.get("schema") == "miw.operation-registry.v1", "SELF_CONTRACT_REGISTRY_INVALID")
    operation_ids = {row.get("operation_id") for row in registry.get("operations", [])}
    require({"explain", "self-contract-check"} <= operation_ids,
            "SELF_CONTRACT_OPERATIONS_UNDECLARED")

    referenced_courts: set[str] = set()
    referenced_nonclaims: set[str] = set()
    referenced_assumptions: set[str] = set()
    checked_paths: set[str] = set()
    referenced_tests: set[str] = set()
    available_tests = _declared_test_ids(Path(project))
    for index, guarantee in enumerate(guarantees):
        path = f"$.guarantees[{index}]"
        require(type(guarantee) is dict and set(guarantee) == GUARANTEE_KEYS,
                "SELF_CONTRACT_GUARANTEE_SHAPE_INVALID", path=path)
        for field in ("guarantee_id", "title", "claim", "scope"):
            _text(guarantee[field], "SELF_CONTRACT_GUARANTEE_TEXT_REQUIRED", path=f"{path}.{field}")
        code_paths = _texts(guarantee["enforcing_paths"], "SELF_CONTRACT_CODE_PATHS_REQUIRED",
                            path=f"{path}.enforcing_paths")
        for code_path in code_paths:
            _code_path(Path(project), code_path, path=f"{path}.enforcing_paths")
            checked_paths.add(code_path)
        guarantee_courts = set(_texts(guarantee["court_ids"], "SELF_CONTRACT_COURTS_REQUIRED",
                                      path=f"{path}.court_ids"))
        require(guarantee_courts <= court_ids, "SELF_CONTRACT_COURT_UNDECLARED", path=path)
        referenced_courts.update(guarantee_courts)
        guarantee_tests = set(_texts(guarantee["test_ids"], "SELF_CONTRACT_TEST_IDS_REQUIRED",
                                     path=f"{path}.test_ids"))
        require(guarantee_tests <= available_tests, "SELF_CONTRACT_TEST_ID_UNRESOLVED", path=path,
                detail=",".join(sorted(guarantee_tests - available_tests)))
        referenced_tests.update(guarantee_tests)
        _texts(guarantee["evidence_schemas"], "SELF_CONTRACT_EVIDENCE_SCHEMAS_REQUIRED",
               path=f"{path}.evidence_schemas")
        _texts(guarantee["invalidated_by"], "SELF_CONTRACT_INVALIDATION_REQUIRED",
               path=f"{path}.invalidated_by")
        guarantee_nonclaims = set(_texts(guarantee["nonclaim_ids"], "SELF_CONTRACT_NONCLAIM_REFS_REQUIRED",
                                         path=f"{path}.nonclaim_ids"))
        guarantee_assumptions = set(_texts(guarantee["assumption_ids"], "SELF_CONTRACT_ASSUMPTION_REFS_REQUIRED",
                                          path=f"{path}.assumption_ids"))
        require(guarantee_nonclaims <= nonclaim_ids, "SELF_CONTRACT_NONCLAIM_UNDECLARED", path=path)
        require(guarantee_assumptions <= assumption_ids, "SELF_CONTRACT_ASSUMPTION_UNDECLARED", path=path)
        referenced_nonclaims.update(guarantee_nonclaims)
        referenced_assumptions.update(guarantee_assumptions)

    for index, nonclaim in enumerate(nonclaims):
        path = f"$.nonclaims[{index}]"
        require(type(nonclaim) is dict and set(nonclaim) == NONCLAIM_KEYS,
                "SELF_CONTRACT_NONCLAIM_SHAPE_INVALID", path=path)
        for field in NONCLAIM_KEYS:
            _text(nonclaim[field], "SELF_CONTRACT_NONCLAIM_TEXT_REQUIRED", path=f"{path}.{field}")
    for index, assumption in enumerate(assumptions):
        path = f"$.trusted_assumptions[{index}]"
        require(type(assumption) is dict and set(assumption) == ASSUMPTION_KEYS,
                "SELF_CONTRACT_ASSUMPTION_SHAPE_INVALID", path=path)
        for field in ASSUMPTION_KEYS:
            _text(assumption[field], "SELF_CONTRACT_ASSUMPTION_TEXT_REQUIRED", path=f"{path}.{field}")

    require(referenced_courts == court_ids, "SELF_CONTRACT_COURT_COVERAGE_INCOMPLETE")
    require(referenced_nonclaims == nonclaim_ids, "SELF_CONTRACT_NONCLAIM_ORPHANED")
    require(referenced_assumptions == assumption_ids, "SELF_CONTRACT_ASSUMPTION_ORPHANED")
    return seal({
        "schema": "miw.self-contract-check.v1", **BOUNDARY,
        "status": "PASSED", "self_contract_root": checked["self_contract_root"],
        "registry_root": root(registry), "ctr_plan_root": root(plan),
        "guarantees": len(guarantees), "nonclaims": len(nonclaims),
        "trusted_assumptions": len(assumptions), "code_paths_checked": len(checked_paths),
        "courts_covered": len(referenced_courts), "tests_resolved": len(referenced_tests),
        "claim_ceiling": "Contract structure and live references only; not independent proof of the declared guarantees.",
    }, "self_contract_check_root")


def explain_self_contract(contract: Mapping[str, Any], project: Path,
                          registry: Mapping[str, Any], plan: Mapping[str, Any],
                          item_id: str | None = None) -> dict[str, Any]:
    """Resolve a guarantee, nonclaim, assumption, or the complete index."""
    validation = validate_self_contract(contract, project, registry, plan)
    checked = dict(contract)
    if item_id is None:
        result: dict[str, Any] = {
            "kind": "INDEX",
            "guarantees": [{"id": row["guarantee_id"], "title": row["title"]}
                           for row in checked["guarantees"]],
            "nonclaims": [{"id": row["nonclaim_id"], "statement": row["statement"]}
                          for row in checked["nonclaims"]],
            "trusted_assumptions": [{"id": row["assumption_id"], "statement": row["statement"]}
                                    for row in checked["trusted_assumptions"]],
        }
        query = "ALL"
    else:
        _text(item_id, "SELF_CONTRACT_ITEM_ID_REQUIRED")
        matches: list[tuple[str, Mapping[str, Any]]] = []
        for kind, rows, key in (
            ("GUARANTEE", checked["guarantees"], "guarantee_id"),
            ("NONCLAIM", checked["nonclaims"], "nonclaim_id"),
            ("TRUSTED_ASSUMPTION", checked["trusted_assumptions"], "assumption_id"),
        ):
            matches.extend((kind, row) for row in rows if row[key] == item_id)
        require(len(matches) == 1, "SELF_CONTRACT_ITEM_UNKNOWN", detail=item_id)
        result = {"kind": matches[0][0], "entry": dict(matches[0][1])}
        query = item_id
    return seal({
        "schema": "miw.self-explanation.v1", **BOUNDARY,
        "status": "EXPLAINED", "query": query,
        "self_contract_root": checked["self_contract_root"],
        "self_contract_check_root": validation["self_contract_check_root"],
        "result": result,
        "evidence_evaluation": "DECLARED_REQUIREMENTS_ONLY",
        "claim_ceiling": "Generated navigation over the sealed self-contract; not law, independent review, or proof by self-reference.",
    }, "explanation_root")


__all__ = ["explain_self_contract", "validate_self_contract"]
