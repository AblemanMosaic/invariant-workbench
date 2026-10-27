from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from uclop.canonical import Refusal, root
from uclop.checkers import evaluate_evidence, make_evidence_material
from uclop.deductive_proofs import (
    SOLVER_RESPONSE_SCHEMA,
    compile_contract,
    evidence_subject,
    make_contract,
    make_solver_request,
    prove_contract,
    THEORY_ROOT,
    verify_proof,
    verify_solver_response,
)
from uclop.obligations import conserve, inventory


def integer(value: int) -> dict:
    return {"op": "INT", "value": value}


def variable(name: str) -> dict:
    return {"op": "VAR", "name": name}


def compare(op: str, left: dict, right: dict) -> dict:
    return {"op": op, "args": [left, right]}


def add(*args: dict) -> dict:
    return {"op": "ADD", "args": list(args)}


def subtract(left: dict, right: dict) -> dict:
    return {"op": "SUB", "args": [left, right]}


def bounded_assignment_contract() -> dict:
    return make_contract(
        contract_id="bounded_assignment",
        subject_root=root({"program": "bounded-assignment"}),
        obligation_id="O_ASSIGN",
        variables=[{"name": "x", "sort": "INT"}, {"name": "y", "sort": "INT"}],
        assumptions=[],
        precondition={"op": "AND", "args": [
            compare("GE", variable("x"), integer(0)),
            compare("LE", variable("x"), integer(5)),
        ]},
        body=[
            {"op": "ASSIGN", "target": "y", "value": add(variable("x"), integer(1))},
            {"op": "ASSERT", "id": "positive_result",
             "formula": compare("GE", variable("y"), integer(1))},
        ],
        postcondition=compare("LE", variable("y"), integer(6)),
    )


def loop_contract() -> dict:
    return make_contract(
        contract_id="countdown",
        subject_root=root({"program": "countdown"}),
        obligation_id="O_COUNTDOWN",
        variables=[{"name": "x", "sort": "INT"}],
        assumptions=[],
        precondition=compare("GE", variable("x"), integer(0)),
        body=[{
            "op": "LOOP",
            "id": "countdown_loop",
            "condition": compare("GT", variable("x"), integer(0)),
            "invariant": compare("GE", variable("x"), integer(0)),
            "decreases": variable("x"),
            "body": [{"op": "ASSIGN", "target": "x",
                      "value": subtract(variable("x"), integer(1))}],
        }],
        postcondition=compare("EQ", variable("x"), integer(0)),
    )


class NativeDeductiveProofTests(unittest.TestCase):
    def test_shipped_fixture_rebuilds_and_rechecks_byte_identically(self):
        workspace = Path(__file__).resolve().parents[1]
        fixture = workspace / "fixtures"
        subsystem = json.loads((workspace / "spec/UCM-NATIVE-DEDUCTIVE-PROOF-V1.json").read_text(encoding="utf-8"))
        self.assertEqual(THEORY_ROOT, subsystem["theory_root"])
        contract = json.loads((fixture / "native-proof-contract.json").read_text(encoding="utf-8"))
        proof = json.loads((fixture / "native-proof-bundle.json").read_text(encoding="utf-8"))
        checked = json.loads((fixture / "native-proof-check.json").read_text(encoding="utf-8"))
        self.assertEqual(proof, prove_contract(contract))
        self.assertEqual(checked, verify_proof(contract, proof))

    def test_straight_line_contract_compiles_proves_and_rechecks(self):
        contract = bounded_assignment_contract()
        compiled = compile_contract(contract)
        self.assertEqual(["ASSERT.positive_result", "POST"],
                         [row["vc_id"] for row in compiled["verification_conditions"]])
        proof = prove_contract(contract)
        self.assertEqual("PROVED", proof["outcome"])
        self.assertTrue(all(row["status"] == "PROVED" for row in proof["proofs"]))
        check = verify_proof(contract, proof)
        self.assertEqual("PASS_CHECKED", check["status"])
        self.assertEqual(evidence_subject(contract), check["evidence_subject"])

    def test_loop_invariant_exit_and_decreases_are_all_proved(self):
        contract = loop_contract()
        compiled = compile_contract(contract)
        self.assertEqual(
            [
                "LOOP.countdown_loop.INIT",
                "LOOP.countdown_loop.PRESERVE",
                "LOOP.countdown_loop.NONNEGATIVE",
                "LOOP.countdown_loop.DECREASES",
                "POST.1",
                "POST.2",
            ],
            [row["vc_id"] for row in compiled["verification_conditions"]],
        )
        proof = prove_contract(contract)
        self.assertEqual("PROVED", proof["outcome"])
        self.assertEqual("PASS_CHECKED", verify_proof(contract, proof)["status"])

    def test_assumption_bound_proof_is_explicit_and_cannot_discharge(self):
        contract = make_contract(
            contract_id="assumed_nonnegative",
            subject_root=root({"program": "assumed"}),
            obligation_id="O_ASSUMED",
            variables=[{"name": "x", "sort": "INT"}],
            assumptions=[compare("GE", variable("x"), integer(0))],
            precondition={"op": "TRUE"},
            body=[],
            postcondition=compare("GE", variable("x"), integer(0)),
        )
        proof = prove_contract(contract)
        self.assertEqual("ASSUMPTION_BOUND", proof["outcome"])
        self.assertEqual("ASSUMPTION_BOUND", verify_proof(contract, proof)["outcome"])
        source = {
            "id": "O_ASSUMED", "kind": "SAFETY", "statement": "x remains nonnegative",
            "source_ref": "contract", "assumptions": [],
            "required_evidence": ["NATIVE_DEDUCTIVE_PROOF"], "severity": "HIGH",
            "evidence_subject": evidence_subject(contract),
        }
        source_inventory = inventory([source], contract["subject_root"])
        target_inventory = inventory([], contract["subject_root"])
        material = make_evidence_material(
            "EXACT_NATIVE_DEDUCTIVE_PROOF_V1",
            obligation_id=source["id"], disposition="DISCHARGED",
            source_inventory_root=source_inventory["inventory_root"],
            target_inventory_root=target_inventory["inventory_root"], target_obligation_ids=[],
            evidence_subject=evidence_subject(contract),
            payload={"contract": contract, "proof_bundle": proof},
        )
        with self.assertRaises(Refusal) as raised:
            evaluate_evidence(material, source_inventory_root=source_inventory["inventory_root"],
                              target_inventory_root=target_inventory["inventory_root"],
                              source_obligation=source, target_obligations=[], disposition="DISCHARGED")
        self.assertEqual("EVIDENCE_DEDUCTIVE_PROOF_NOT_UNCONDITIONAL", raised.exception.code)

    def test_unknown_is_checked_as_unknown_without_becoming_a_proof(self):
        contract = make_contract(
            contract_id="unknown_bound",
            subject_root=root({"program": "unknown"}),
            obligation_id="O_UNKNOWN",
            variables=[{"name": "x", "sort": "INT"}], assumptions=[],
            precondition={"op": "TRUE"}, body=[],
            postcondition=compare("LE", variable("x"), integer(0)),
        )
        proof = prove_contract(contract)
        self.assertEqual("UNKNOWN", proof["outcome"])
        self.assertEqual("UNKNOWN", verify_proof(contract, proof)["outcome"])

    def test_certificate_tamper_and_subject_substitution_refuse(self):
        contract = bounded_assignment_contract()
        proof = prove_contract(contract)
        tampered = deepcopy(proof)
        certificate = tampered["proofs"][0]["certificate"]
        certificate["trace"][-1]["constraint"]["bound"] = 0
        certificate["certificate_root"] = root({key: value for key, value in certificate.items()
                                                 if key != "certificate_root"})
        tampered["proof_bundle_root"] = root({key: value for key, value in tampered.items()
                                               if key != "proof_bundle_root"})
        with self.assertRaises(Refusal):
            verify_proof(contract, tampered)
        substituted = deepcopy(contract)
        substituted["subject_root"] = root({"program": "other"})
        substituted["contract_root"] = root({key: value for key, value in substituted.items()
                                              if key != "contract_root"})
        with self.assertRaises(Refusal) as raised:
            verify_proof(substituted, proof)
        self.assertEqual("PROOF_BUNDLE_SUBJECT_MISMATCH", raised.exception.code)

    def test_untrusted_solver_response_is_accepted_only_after_kernel_recheck(self):
        contract = bounded_assignment_contract()
        request = make_solver_request(contract)
        proof = prove_contract(contract)
        body = {
            "schema": SOLVER_RESPONSE_SCHEMA,
            "request_root": request["request_root"],
            "solver_identity": {"name": "fixture-search", "version": "1"},
            "proof_bundle": proof,
            "standing": "INFORMATION_ONLY",
            "authority_effect": "NONE",
        }
        response = {**body, "response_root": root(body)}
        self.assertEqual("PASS_CHECKED", verify_solver_response(contract, request, response)["status"])
        response = deepcopy(response)
        response["proof_bundle"]["proofs"][0]["status"] = "PROVED"
        response["proof_bundle"]["proofs"][0]["certificate"] = None
        response["proof_bundle"]["proofs"][0]["diagnostic"] = None
        response["proof_bundle"]["proof_bundle_root"] = root({key: value for key, value in response["proof_bundle"].items()
                                                               if key != "proof_bundle_root"})
        response["response_root"] = root({key: value for key, value in response.items()
                                          if key != "response_root"})
        with self.assertRaises(Refusal):
            verify_solver_response(contract, request, response)

    def test_unconditional_proof_discharges_exact_subject_bound_obligation(self):
        contract = bounded_assignment_contract()
        proof = prove_contract(contract)
        source = {
            "id": "O_ASSIGN", "kind": "SAFETY", "statement": "result remains bounded",
            "source_ref": "contract", "assumptions": [],
            "required_evidence": ["NATIVE_DEDUCTIVE_PROOF"], "severity": "CRITICAL",
            "evidence_subject": evidence_subject(contract),
        }
        source_inventory = inventory([source], contract["subject_root"])
        target_inventory = inventory([], contract["subject_root"])
        material = make_evidence_material(
            "EXACT_NATIVE_DEDUCTIVE_PROOF_V1",
            obligation_id=source["id"], disposition="DISCHARGED",
            source_inventory_root=source_inventory["inventory_root"],
            target_inventory_root=target_inventory["inventory_root"], target_obligation_ids=[],
            evidence_subject=evidence_subject(contract),
            payload={"contract": contract, "proof_bundle": proof},
        )
        receipt = evaluate_evidence(
            material, source_inventory_root=source_inventory["inventory_root"],
            target_inventory_root=target_inventory["inventory_root"], source_obligation=source,
            target_obligations=[], disposition="DISCHARGED",
        )
        self.assertEqual("PASS_CHECKED", receipt["status"])
        mapped = conserve(
            source_inventory, target_inventory,
            [{"from_id": source["id"], "to_ids": [], "disposition": "DISCHARGED",
              "edge_kind": "CHECKS", "evidence_refs": [receipt["receipt_root"]],
              "reason": "native kernel checked exact contract"}],
            pass_id="NATIVE_PROOF_DISCHARGE",
            evidence_records={receipt["receipt_root"]: receipt},
            evidence_materials={material["evidence_root"]: material},
        )
        self.assertEqual("PASS_CONSERVED", mapped["status"])
        changed = deepcopy(material)
        changed["evidence_subject"]["subject_root"] = root({"program": "other"})
        changed["evidence_root"] = root({key: value for key, value in changed.items() if key != "evidence_root"})
        with self.assertRaises(Refusal):
            evaluate_evidence(changed, source_inventory_root=source_inventory["inventory_root"],
                              target_inventory_root=target_inventory["inventory_root"],
                              source_obligation=source, target_obligations=[], disposition="DISCHARGED")

    def test_malformed_and_nonlinear_contracts_refuse_typed(self):
        contract = bounded_assignment_contract()
        contract["body"][0]["value"] = {"op": "MUL", "args": [variable("x"), variable("y")]}
        contract["contract_root"] = root({key: value for key, value in contract.items() if key != "contract_root"})
        with self.assertRaises(Refusal) as raised:
            compile_contract(contract)
        self.assertEqual("PROOF_TERM_OP_UNSUPPORTED", raised.exception.code)


if __name__ == "__main__":
    unittest.main()
