"""Fail-closed realization-space kernel used by the Invariant Workbench.

This is a local engineering contract.  It carries no corpus, release, or
Governor standing.  Structural JSON Schema checks are complemented here by
the cross-field and reference checks that JSON Schema cannot express cleanly.
"""
from __future__ import annotations

import ast
import re
import unicodedata
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

from .common import BOUNDARY, Refusal, canonical_bytes, digest, read_json, require, root, seal

CONTRACT_SCHEMA = "miw.invariant-evidence-space-contract.v0.1"
REGISTRY_SCHEMA = "miw.workbench-realizer-registry.v0.1"
DICTIONARY_SCHEMA = "miw.workbench-capability-dictionary.v0.1"
EXPRESSION_LANGUAGE = "miw.rsc.expr.v0.1"

OPERATIONS = frozenset({
    "ENUMERATE", "VALIDATE", "NORMALIZE", "SAMPLE", "SELECT", "LOWER",
    "REALIZE", "COMPARE", "EXPLAIN", "RECEIPT",
})
LOWERING_RESULTS = frozenset({"EXACT", "BOUNDED", "FALLBACK", "LOSSY", "REFUSED"})
SUPPORT = frozenset({"SUPPORTED", "EXPERIMENTAL", "FALLBACK", "UNSUPPORTED"})
STANDINGS = frozenset({"DECLARED", "MEASURED"})
_ID = re.compile(r"[A-Z][A-Z0-9_]{0,63}\Z")
_HEX = re.compile(r"[0-9a-f]{64}\Z")


def _semantic_value_guard(value: Any) -> None:
    """Keep rooted RSC values portable and exact before canonical encoding."""
    if type(value) is float:
        raise Refusal("RSC_FLOAT_REFUSED")
    if type(value) is str:
        require(unicodedata.normalize("NFC", value) == value, "RSC_UNICODE_NORMALIZATION_REFUSED")
    elif type(value) is list:
        for item in value:_semantic_value_guard(item)
    elif type(value) is dict:
        for key, item in value.items():
            _semantic_value_guard(key);_semantic_value_guard(item)


def _ids(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    require(type(rows) is list and all(type(x) is dict for x in rows), "RSC_ARRAY_REQUIRED", detail=label)
    result = {}
    for row in rows:
        value = row.get("id")
        require(type(value) is str and _ID.fullmatch(value) is not None, "RSC_ID_INVALID", detail=label)
        require(value not in result, "RSC_DUPLICATE_ID", detail=value)
        result[value] = row
    return result


def _domain(axis: Mapping[str, Any], value: Any) -> bool:
    domain = axis["domain"]
    kind = axis["value_type"]
    if kind == "ENUM":
        return type(value) is str and value in domain.get("values", [])
    if kind == "BOOLEAN":
        return type(value) is bool
    if kind == "INTEGER":
        return type(value) is int and domain["minimum"] <= value <= domain["maximum"]
    if kind == "DECIMAL":
        if type(value) is not str or re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?", value) is None:
            return False
        from decimal import Decimal, InvalidOperation
        try:
            number = Decimal(value)
            return Decimal(domain["minimum"]) <= number <= Decimal(domain["maximum"])
        except InvalidOperation:
            return False
    if kind == "REFERENCE":
        return type(value) is str and re.fullmatch(domain["pattern"], value) is not None
    return False


_ALLOWED_AST = (
    ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not,
    ast.Compare, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Name, ast.Load, ast.Constant,
)


def evaluate(expression: str, values: Mapping[str, Any]) -> bool:
    require(type(expression) is str and 0 < len(expression) <= 1000,
            "RSC_EXPRESSION_LANGUAGE_REFUSED")
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise Refusal("RSC_EXPRESSION_LANGUAGE_REFUSED") from exc
    require(all(isinstance(node, _ALLOWED_AST) for node in ast.walk(tree)),
            "RSC_EXPRESSION_LANGUAGE_REFUSED")
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    require(names <= set(values), "RSC_EXPRESSION_REFERENCE_UNKNOWN",
            detail=",".join(sorted(names - set(values))))
    require(all(type(node.value) in (str, int, bool, type(None))
                for node in ast.walk(tree) if isinstance(node, ast.Constant)),
            "RSC_EXPRESSION_LITERAL_REFUSED")
    return bool(eval(compile(tree, "<miw-rsc>", "eval"), {"__builtins__": {}}, dict(values)))


def validate_dictionary(dictionary: Mapping[str, Any]) -> dict[str, Any]:
    _semantic_value_guard(dictionary)
    require(type(dictionary) is dict and dictionary.get("schema") == DICTIONARY_SCHEMA,
            "RSC_CAPABILITY_DICTIONARY_SCHEMA_REFUSED")
    entries = _ids(dictionary.get("capabilities"), "capabilities")
    for cap in entries.values():
        require(type(cap.get("meaning")) is str and cap["meaning"], "RSC_CAPABILITY_MEANING_REQUIRED")
        require(cap.get("state_effect_class") in {"PRESENTATION", "ANALYSIS", "LOCAL_EXECUTION", "EXTERNAL_EXECUTION"},
                "RSC_CAPABILITY_EFFECT_CLASS_REFUSED", detail=cap["id"])
        require(type(cap.get("consumed_value_types")) is list and
                all(type(x) is str for x in cap["consumed_value_types"]),
                "RSC_CAPABILITY_VALUE_TYPES_REFUSED", detail=cap["id"])
        require(type(cap.get("measurable_metrics")) is list and
                all(type(x) is str for x in cap["measurable_metrics"]),
                "RSC_CAPABILITY_METRICS_REFUSED", detail=cap["id"])
    checked = {"capability_count": len(entries), "dictionary_root": root(dictionary)}
    return checked


def validate_registry(registry: Mapping[str, Any], dictionary: Mapping[str, Any]) -> dict[str, Any]:
    _semantic_value_guard(registry)
    checked_dictionary = validate_dictionary(dictionary)
    require(type(registry) is dict and registry.get("schema") == REGISTRY_SCHEMA,
            "RSC_REGISTRY_SCHEMA_REFUSED")
    require(registry.get("authority_effect") == "NONE", "RSC_AUTHORITY_EFFECT_REFUSED")
    require(registry.get("dictionary_root") == checked_dictionary["dictionary_root"],
            "RSC_CAPABILITY_DICTIONARY_ROOT_MISMATCH")
    known = set(_ids(dictionary["capabilities"], "capabilities"))
    profiles = _ids(registry.get("profiles"), "profiles")
    for profile in profiles.values():
        require(profile.get("uniform_across_realizers") is True or type(profile.get("realizer_overrides")) is dict,
                "RSC_PROFILE_DELTA_POLICY_REQUIRED", detail=profile["id"])
        declarations = profile.get("realizer_capabilities")
        require(type(declarations) is dict, "RSC_REALIZER_CAPABILITIES_REQUIRED", detail=profile["id"])
        for capability, declaration in declarations.items():
            require(capability in known, "RSC_CAPABILITY_UNKNOWN", detail=capability)
            require(type(declaration) is dict and declaration.get("status") in SUPPORT and
                    declaration.get("standing") in STANDINGS,
                    "RSC_CAPABILITY_DECLARATION_REFUSED", detail=capability)
            if declaration["standing"] == "MEASURED":
                require(_HEX.fullmatch(str(declaration.get("evidence_root", ""))) is not None and
                        type(declaration.get("host_id")) is str and declaration["host_id"] and
                        type(declaration.get("adapter_version")) is str and declaration["adapter_version"],
                        "RSC_MEASURED_EVIDENCE_REQUIRED", detail=capability)
            if declaration["status"] == "FALLBACK":
                require(declaration.get("fallback_to") in known and
                        type(declaration.get("known_losses")) is list and declaration["known_losses"],
                        "RSC_FALLBACK_DECLARATION_REFUSED", detail=capability)
            if declaration["status"] == "EXPERIMENTAL":
                require(declaration.get("experimental_result") in {"BOUNDED", "REFUSED"} and
                        type(declaration.get("opt_in_required")) is bool,
                        "RSC_EXPERIMENTAL_DECLARATION_REFUSED", detail=capability)
    return {"profile_count": len(profiles), **checked_dictionary, "registry_root": root(registry)}


def validate_contract(contract: Mapping[str, Any], dictionary: Mapping[str, Any] | None = None) -> dict[str, Any]:
    _semantic_value_guard(contract)
    require(type(contract) is dict and contract.get("schema") == CONTRACT_SCHEMA, "RSC_SCHEMA_REFUSED")
    require(contract.get("authority", {}).get("authority_effect") == "NONE" and
            contract.get("authority", {}).get("self_admission") is False and
            contract.get("authority", {}).get("release_gate") is False and
            contract.get("authority", {}).get("track_a_dependency") == "NONE",
            "RSC_AUTHORITY_EFFECT_REFUSED")
    operations = contract.get("operations")
    require(type(operations) is list and operations and set(operations) <= OPERATIONS,
            "RSC_OPERATIONS_REFUSED")
    axes = _ids(contract.get("axes"), "axes")
    for axis in axes.values():
        required = {"id", "label", "value_type", "domain", "default", "ownership", "mutability",
                    "continuity", "state_effect", "effect_owner", "apply_mode", "persistence_effect",
                    "replay_effect", "authority_effect", "lockable"}
        require(required <= set(axis), "RSC_AXIS_FIELD_MISSING", detail=axis["id"])
        require(axis["value_type"] in {"ENUM", "BOOLEAN", "INTEGER", "DECIMAL", "REFERENCE"},
                "RSC_AXIS_TYPE_REFUSED", detail=axis["id"])
        require(type(axis["domain"]) is dict and _domain(axis, axis["default"]),
                "RSC_AXIS_DOMAIN_REFUSED", detail=axis["id"])
        require(axis["authority_effect"] == "NONE", "RSC_AXIS_AUTHORITY_REFUSED", detail=axis["id"])
        if axis["state_effect"] in {"SIMULATION_RULE", "WORLD_GENERATION", "PERSISTENCE_SCHEMA"}:
            require(axis["apply_mode"] not in {"IMMEDIATE", "FRAME_BOUNDARY"},
                    "RSC_APPLY_MODE_REFUSED", detail=axis["id"])
        hazardous = (axis["ownership"], axis["mutability"], axis["replay_effect"])
        require(hazardous != ("ADAPTIVE", "FRAME", "SIMULATION_DETERMINISM"),
                "RSC_REPLAY_DETERMINISM_REFUSED", detail=axis["id"])
    for constraint in contract.get("constraints", []):
        require(type(constraint) is dict and constraint.get("expression_language") == EXPRESSION_LANGUAGE,
                "RSC_EXPRESSION_LANGUAGE_REFUSED")
        evaluate(constraint.get("expression", ""), {k: v["default"] for k, v in axes.items()})
        require(type(constraint.get("refusal_code")) is str, "RSC_REFUSAL_CODE_REQUIRED")
    regions = _ids(contract.get("preferred_regions", []), "preferred_regions")
    defaults = {k: v["default"] for k, v in axes.items()}
    for region in regions.values():
        require(region.get("predicate_language") == EXPRESSION_LANGUAGE, "RSC_EXPRESSION_LANGUAGE_REFUSED")
        values = {**defaults, **region.get("profile_defaults", {})}
        require(set(values) == set(defaults) and all(_domain(axes[k], v) for k, v in values.items()),
                "RSC_PREFERRED_REGION_DOMAIN_REFUSED", detail=region["id"])
        require(evaluate(region["predicate"], values), "RSC_PREFERRED_REGION_REFUSED", detail=region["id"])
        for constraint in contract.get("constraints", []):
            if constraint.get("severity") == "HARD":
                require(evaluate(constraint["expression"], values),
                        "RSC_PREFERRED_REGION_OUTSIDE_ADMISSIBLE", detail=region["id"])
    selection = contract.get("selection", {})
    require(selection.get("default_policy") in selection.get("policies", []),
            "RSC_SELECTION_DEFAULT_POLICY_REFUSED")
    require(type(selection.get("fallback_policy")) is str and selection["fallback_policy"],
            "RSC_SELECTION_FALLBACK_REQUIRED")
    require(type(selection.get("locks")) is list and
            set(selection["locks"]) <= {k for k, v in axes.items() if v["lockable"]},
            "RSC_SELECTION_LOCK_REFUSED")
    known_capabilities = None
    if dictionary is not None:
        known_capabilities = set(_ids(dictionary["capabilities"], "capabilities"))
    targets = _ids(contract.get("lowering", {}).get("targets", []), "targets")
    allowed = contract.get("lowering", {}).get("allowed_results")
    require(type(allowed) is list and set(allowed) <= LOWERING_RESULTS and "REFUSED" in allowed,
            "RSC_LOWERING_RESULTS_REFUSED")
    for target in targets.values():
        required = target.get("required_realizer_capabilities")
        require(type(required) is list and all(type(x) is str for x in required),
                "RSC_TARGET_CAPABILITIES_REFUSED", detail=target["id"])
        if known_capabilities is not None:
            require(set(required) <= known_capabilities, "RSC_CAPABILITY_UNKNOWN", detail=target["id"])
        require(type(target.get("axis_mapping")) is list and all(
            type(x) is dict and set(x) == {"axis_id", "target_setting", "transform"} and x["axis_id"] in axes
            for x in target["axis_mapping"]), "RSC_AXIS_MAPPING_REFUSED", detail=target["id"])
        require(type(target.get("refusal_conditions")) is list and
                type(target.get("output_schema")) is str and
                type(target.get("required_evidence_fields")) is list,
                "RSC_TARGET_FIELD_MISSING", detail=target["id"])
    revision = contract.get("revision")
    if revision is not None:
        require(type(revision) is dict and _HEX.fullmatch(str(revision.get("predecessor_root", ""))) is not None and
                type(revision.get("trigger_evidence_roots")) is list and revision["trigger_evidence_roots"] and
                all(_HEX.fullmatch(str(x)) is not None for x in revision["trigger_evidence_roots"]),
                "RSC_REVISION_REFUSED")
    return {"contract_root": root(contract), "axis_count": len(axes), "target_count": len(targets),
            "operation_count": len(operations)}


def select_configuration(contract: Mapping[str, Any], requested: Mapping[str, Any] | None = None,
                         *, region_id: str | None = None) -> dict[str, Any]:
    checked = validate_contract(contract)
    axes = _ids(contract["axes"], "axes")
    values = {k: deepcopy(v["default"]) for k, v in axes.items()}
    if region_id is not None:
        regions = _ids(contract.get("preferred_regions", []), "preferred_regions")
        require(region_id in regions, "RSC_REGION_UNKNOWN", detail=region_id)
        values.update(deepcopy(regions[region_id].get("profile_defaults", {})))
    requested = dict(requested or {})
    require(set(requested) <= set(axes), "RSC_AXIS_UNKNOWN")
    locked = set(contract["selection"]["locks"])
    require(not (locked & set(requested)), "RSC_AXIS_LOCKED", detail=",".join(sorted(locked & set(requested))))
    values.update(requested)
    for key, value in values.items():
        require(_domain(axes[key], value), "RSC_AXIS_DOMAIN_REFUSED", detail=key)
    for constraint in contract.get("constraints", []):
        if constraint.get("severity") == "HARD":
            require(evaluate(constraint["expression"], values), constraint["refusal_code"])
    body = {"schema": "miw.realization-selection.v0.1", **BOUNDARY,
            "contract_root": checked["contract_root"], "region_id": region_id,
            "values": values, "locks": sorted(locked)}
    return seal(body, "selection_root")


def lower_configuration(contract: Mapping[str, Any], selection: Mapping[str, Any],
                        registry: Mapping[str, Any], dictionary: Mapping[str, Any],
                        *, target_id: str, profile_id: str, allow_experimental: bool = False) -> dict[str, Any]:
    checked = validate_contract(contract, dictionary)
    registry_checked = validate_registry(registry, dictionary)
    require(selection.get("contract_root") == checked["contract_root"], "RSC_SELECTION_CONTRACT_MISMATCH")
    targets = _ids(contract["lowering"]["targets"], "targets")
    profiles = _ids(registry["profiles"], "profiles")
    require(target_id in targets, "RSC_TARGET_UNKNOWN", detail=target_id)
    require(profile_id in profiles, "RSC_PROFILE_UNKNOWN", detail=profile_id)
    target, profile = targets[target_id], profiles[profile_id]
    resolutions = []
    rank = {"EXACT": 0, "BOUNDED": 1, "FALLBACK": 2, "LOSSY": 3, "REFUSED": 4}
    result = "EXACT"
    for capability in target["required_realizer_capabilities"]:
        declaration = profile["realizer_capabilities"].get(capability)
        if declaration is None:
            row = {"capability": capability, "result": "REFUSED", "code": "RSC_CAPABILITY_UNDECLARED"}
        elif declaration["status"] == "SUPPORTED":
            row = {"capability": capability, "result": declaration.get("lowering_result", "EXACT")}
        elif declaration["status"] == "FALLBACK":
            row = {"capability": capability, "result": "FALLBACK",
                   "fallback_to": declaration["fallback_to"], "known_losses": declaration["known_losses"]}
        elif declaration["status"] == "EXPERIMENTAL" and allow_experimental and not declaration["opt_in_required"]:
            row = {"capability": capability, "result": declaration["experimental_result"]}
        elif declaration["status"] == "EXPERIMENTAL" and allow_experimental:
            row = {"capability": capability, "result": declaration["experimental_result"], "opted_in": True}
        else:
            row = {"capability": capability, "result": "REFUSED",
                   "code": "RSC_CAPABILITY_UNSUPPORTED" if declaration["status"] == "UNSUPPORTED" else "RSC_EXPERIMENTAL_OPT_IN_REQUIRED"}
        require(row["result"] in LOWERING_RESULTS, "RSC_STATUS_ALGEBRA_REFUSED")
        resolutions.append(row)
        if rank[row["result"]] > rank[result]:
            result = row["result"]
    require(result in contract["lowering"]["allowed_results"], "RSC_LOWERING_RESULT_NOT_ALLOWED")
    body = {"schema": "miw.realization-lowering.v0.1", **BOUNDARY,
            "contract_root": checked["contract_root"], "selection_root": selection["selection_root"],
            "registry_root": registry_checked["registry_root"], "target_id": target_id,
            "profile_id": profile_id, "result": result, "resolutions": resolutions,
            "preserved": target.get("preserved", []), "known_losses": target.get("known_losses", []),
            "output_schema": target["output_schema"]}
    return seal(body, "lowering_root")


def validate_bundle(contract_path: Path, registry_path: Path, dictionary_path: Path) -> dict[str, Any]:
    contract, registry, dictionary = read_json(contract_path), read_json(registry_path), read_json(dictionary_path)
    return seal({"schema": "miw.realization-bundle-check.v0.1", **BOUNDARY,
                 "contract": validate_contract(contract, dictionary),
                 "registry": validate_registry(registry, dictionary)}, "check_root")
