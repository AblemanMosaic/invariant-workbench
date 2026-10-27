from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from uclop import project_intelligence as pi
from uclop.canonical import Refusal, root, strict_loads
from uclop.custody import OpaqueEd25519KeyStore
from uclop.protected_state import InMemoryMonotonicAnchor, ProtectedStateStore
from uclop.workbench_manager import (WorkbenchManager,
                                     authorize_recovery, create_plan, validate_plan)
from uclop.workbench_orientation import build_fixture_orientation
from uclop.workbench_workers import BoundedWorker, snapshot_source


def project_for(source_root: str) -> dict:
    records = [
        {"id": "ART-TARGET", "kind": "IMPLEMENTATION_ARTIFACT", "title": "Target",
         "summary": "Candidate artifact", "state": "PLANNED", "depends_on": ["REQ-READ"],
         "path": "README.txt", "sha256": None},
        {"id": "REQ-READ", "kind": "REQUIREMENT", "title": "Read",
         "summary": "Inspect source", "state": "OPEN", "depends_on": [],
         "criterion": "Source read against exact pin"},
        {"id": "VER-REAL", "kind": "VERIFICATION_OBLIGATION", "title": "Real test",
         "summary": "Execute trusted tests", "state": "OPEN", "depends_on": ["ART-TARGET"], "evidence": []},
    ]
    body = {"schema": pi.SCHEMA, "project_id": "MANAGER-FIXTURE", "baseline": {
        "subject": "PINNED-TRUSTED-FIXTURE", "source_root": source_root,
        "review_disposition": "UNREVIEWED"}, "standing": "INFORMATION_ONLY",
        "authority_effect": "NONE", "records": records}
    return {**body, "snapshot_root": pi.rooted(body)}


class WorkbenchManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ucm-manager-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        (self.source / "tests").mkdir(parents=True)
        (self.source / "README.txt").write_bytes(b"original\n")
        (self.source / "tests/__init__.py").write_bytes(b"")
        self.test_source = (b"import unittest\nclass Real(unittest.TestCase):\n"
                            b"    def test_one(self):\n        self.assertEqual(2 + 3, 5)\n")
        (self.source / "tests/test_sample.py").write_bytes(self.test_source)
        self.snapshot = snapshot_source(self.source)
        self.project = project_for(self.snapshot["source_root"])
        self.fixture = build_fixture_orientation(roots={"project": self.project["snapshot_root"],
                                                         "source": self.snapshot["source_root"]})
        self.context = self.fixture["context"]
        self.pins = {name: self.context[name] for name in (
            "project_root", "source_root", "registry_root", "policy_root", "charter_root", "grant_root", "jurisdiction_root")}
        self.actions = {
            "REQ-READ": {"operation": "INSPECT_ARTIFACTS", "payload": {"paths": ["README.txt"]}},
            "ART-TARGET": {"operation": "PREPARE_CANDIDATE", "payload": {"changes": [{"path": "README.txt",
                "original_sha256": hashlib.sha256(b"original\n").hexdigest(),
                "replacement_base64": base64.b64encode(b"proposed\n").decode()}]}},
            "VER-REAL": {"operation": "RUN_TESTS", "payload": {"modules": ["tests.test_sample"],
                "candidate_task_id": "TASK-ART-TARGET"}},
        }
        self.plan = create_plan(self.project, pins=self.pins, task_actions=self.actions)
        self.keys = OpaqueEd25519KeyStore()
        self.state_handle = self.keys.install_fixture_seed("WITNESS", b"S" * 32)
        self.worker_handle = self.keys.install_fixture_seed("NODE", b"W" * 32)
        self.anchor = InMemoryMonotonicAnchor()
        self.store = ProtectedStateStore(self.base / "state", anchor=self.anchor,
                                          keys=self.keys, signing_handle=self.state_handle)
        self.worker = BoundedWorker(source_directory=self.source, source_manifest=self.snapshot,
            output_directory=self.base / "outputs", bindings=self.pins, tenant_id=self.context["tenant_id"],
            provider=self.keys, signing_handle=self.worker_handle, expected_issuer=self.keys.identity(self.worker_handle),
            maximum_artifact_bytes=self.context["budgets"]["max_artifact_bytes"],
            trusted_tests={"tests.test_sample": {"path": "tests/test_sample.py",
                "sha256": hashlib.sha256(self.test_source).hexdigest(),
                "test_ids": ["tests.test_sample.Real.test_one"]}})

    def args(self, **overrides):
        args = {"project": self.project, "plan": self.plan, "orientation": self.context,
                "orientation_pins": self.fixture["external_pins"],
                "worker_identity": self.keys.identity(self.worker_handle),
                "worker_root": self.worker.worker_root, "now": 1000}
        args.update(overrides)
        return args

    def manager(self, **overrides):
        return WorkbenchManager(self.store, expected_head={"sequence": 0, "head": "GENESIS"}, **self.args(**overrides))

    def reopen(self, head, **overrides):
        return WorkbenchManager(self.store, expected_head=head, **self.args(**overrides))

    def refused(self, fn, code):
        with self.assertRaises(Refusal) as caught:
            fn()
        self.assertEqual(code, caught.exception.code)

    def start(self, manager, head=None, tid="TASK-REQ-READ", oid="op-read"):
        return manager.begin_dispatch(tid, oid, "dispatcher-one", expected_head=head or manager.current_head, now=1000)

    def test_real_inspection_edit_proposal_and_tests_complete_exact_plan(self):
        manager = self.manager()
        current = manager.current_head
        for task, oid in (("TASK-REQ-READ", "op-read"), ("TASK-ART-TARGET", "op-prepare"), ("TASK-VER-REAL", "op-test")):
            result = manager.execute(task, oid, "dispatcher-one", self.worker, expected_head=current, now=1000)
            current = result["current_head"]
        self.assertEqual("COMPLETE_INFORMATION_ONLY", result["status"])
        self.assertEqual([], result["project_obligations_satisfied"])
        self.assertEqual(3, result["budget_spent_units"])
        self.assertEqual(b"original\n", (self.source / "README.txt").read_bytes())
        self.assertEqual(b"proposed\n", (self.base / "outputs/op-prepare/candidate/README.txt").read_bytes())
        prepared_result = result["operations"]["op-prepare"]["result"]
        test_result = result["operations"]["op-test"]["result"]
        self.assertEqual(root(prepared_result["receipt"]),
                         test_result["evidence"]["result"]["candidate_receipt_root"])
        self.assertEqual(prepared_result["evidence"]["result"]["candidate_manifest"]["source_root"],
                         test_result["evidence"]["result"]["invocation"]["source_root"])
        reopened = self.reopen(current)
        self.assertEqual("COMPLETE_INFORMATION_ONLY", reopened.status(expected_head=current, now=1000)["status"])

    def test_candidate_drift_refuses_before_test_dispatch_is_recorded(self):
        manager = self.manager(); current = manager.current_head
        for task, oid in (("TASK-REQ-READ", "drift-read"), ("TASK-ART-TARGET", "drift-prepare")):
            completed = manager.execute(task, oid, "dispatcher-one", self.worker,
                                        expected_head=current, now=1000)
            current = completed["current_head"]
        candidate = self.base / "outputs/drift-prepare/candidate/README.txt"
        candidate.write_bytes(b"changed after preparation\n")
        with self.assertRaisesRegex(Refusal, "WORKER_CANDIDATE_OUTPUT_DRIFT"):
            manager.begin_dispatch("TASK-VER-REAL", "drift-test", "dispatcher-one",
                                   expected_head=current, now=1000, worker=self.worker)
        self.assertEqual(current, manager.status(expected_head=current, now=1000)["current_head"])

    def test_plan_exact_coverage_and_dependency_edges_rechecked(self):
        changed = deepcopy(self.plan)
        changed["tasks"].pop()
        changed["plan_root"] = root({k: v for k, v in changed.items() if k != "plan_root"})
        self.refused(lambda: validate_plan(changed, self.project, pins=self.pins), "WORKBENCH_TASK_COVERAGE_INVALID")
        changed = deepcopy(self.plan)
        changed["tasks"][0]["depends_on"] = []
        changed["plan_root"] = root({k: v for k, v in changed.items() if k != "plan_root"})
        self.refused(lambda: validate_plan(changed, self.project, pins=self.pins), "WORKBENCH_PLAN_CONTRACT_MISMATCH")

    def test_partial_project_graph_cannot_downgrade_qualification(self):
        self.assertEqual("QUALIFICATION", self.plan["required_lane"])
        altered = deepcopy(self.plan)
        altered["required_lane"] = "FAST"
        altered["plan_root"] = root({k: v for k, v in altered.items() if k != "plan_root"})
        self.refused(lambda: validate_plan(altered, self.project, pins=self.pins), "WORKBENCH_PLAN_CONTRACT_MISMATCH")

    def test_dependency_must_finish_before_consuming_task(self):
        manager = self.manager()
        self.refused(lambda: self.start(manager, tid="TASK-ART-TARGET", oid="out-of-order"),
                     "WORKBENCH_DEPENDENCY_NOT_COMPLETE")
        self.assertEqual(0, manager.status(expected_head=manager.current_head, now=1000)["budget_spent_units"])

    def test_stale_external_head_and_genesis_reuse_refuse(self):
        manager = self.manager()
        old = dict(manager.current_head)
        started = self.start(manager)
        self.refused(lambda: self.reopen(old), "WORKBENCH_STALE_EXTERNAL_HEAD")
        self.refused(lambda: self.manager(), "WORKBENCH_STALE_EXTERNAL_HEAD")
        self.assertEqual("RECOVERY_REQUIRED", self.reopen(started["current_head"]).status(expected_head=started["current_head"], now=1000)["status"])

    def test_two_sessions_share_exact_head_and_single_dispatcher(self):
        first = self.manager()
        second_fixture = build_fixture_orientation(nonce_label="session-two", roots={
            "project": self.project["snapshot_root"], "source": self.snapshot["source_root"]})
        second = self.reopen(first.current_head, orientation=second_fixture["context"], orientation_pins=second_fixture["external_pins"])
        old = dict(first.current_head)
        started = self.start(first)
        self.refused(lambda: self.start(second, old, oid="other"), "WORKBENCH_STALE_EXTERNAL_HEAD")
        self.refused(lambda: self.start(second, started["current_head"], oid="other"), "WORKBENCH_DISPATCHER_BUSY")

    def test_idempotent_return_never_reexecutes_and_alias_refuses(self):
        manager = self.manager()
        result = manager.execute("TASK-REQ-READ", "op-read", "dispatcher-one", self.worker,
                                 expected_head=manager.current_head, now=1000)
        with patch.object(self.worker, "execute", side_effect=AssertionError("repeat")):
            repeated = manager.execute("TASK-REQ-READ", "op-read", "dispatcher-two", self.worker,
                                       expected_head=result["current_head"], now=1000)
        self.assertTrue(repeated["idempotent"])
        self.refused(lambda: self.start(manager, result["current_head"], tid="TASK-ART-TARGET", oid="op-read"),
                     "WORKBENCH_IDEMPOTENCY_CONFLICT")

    def test_forged_receipt_and_wrong_subject_never_complete(self):
        manager = self.manager()
        started = self.start(manager)
        actual = self.worker.execute(started["ticket"]["request"])
        changed = deepcopy(actual)
        changed["receipt"]["body"]["source_root"] = root("other")
        self.refused(lambda: manager.complete_dispatch(started["ticket"], changed,
            expected_head=started["current_head"], now=1000), "SIGNED_BODY_ROOT_MISMATCH")
        changed = deepcopy(actual)
        changed["receipt"]["body"]["task_id"] = "TASK-OTHER"
        from uclop.workbench_workers import RECEIPT_DOMAIN
        changed["receipt"] = self.keys.sign(self.worker_handle, RECEIPT_DOMAIN, changed["receipt"]["body"])
        self.refused(lambda: manager.complete_dispatch(started["ticket"], changed,
            expected_head=started["current_head"], now=1000), "WORKER_RECEIPT_DERIVATION_MISMATCH")
        self.assertEqual("RECOVERY_REQUIRED", manager.status(expected_head=started["current_head"], now=1000)["status"])

    def test_before_worker_interruption_requires_authenticated_no_execution(self):
        manager = self.manager()
        started = self.start(manager)
        reopened = self.reopen(started["current_head"])
        self.refused(lambda: reopened.execute("TASK-REQ-READ", "op-read", "new-dispatcher", self.worker,
            expected_head=started["current_head"], now=1000), "WORKBENCH_RECONCILIATION_REQUIRED")
        attestation = self.worker.attest_not_executed(started["ticket"]["request"])
        reconciled = reopened.reconcile_not_executed(started["ticket"], attestation,
                                                    expected_head=started["current_head"], now=1000)
        self.assertEqual("PENDING", reconciled["tasks"]["TASK-REQ-READ"]["state"])
        retried = reopened.execute("TASK-REQ-READ", "new-operation", "dispatcher", self.worker,
                                   expected_head=reconciled["current_head"], now=1000)
        self.assertEqual(2, retried["tasks"]["TASK-REQ-READ"]["attempts"])

    def test_worker_preflight_refusal_leaves_manager_state_untouched(self):
        manager = self.manager(); original = dict(manager.current_head)
        with patch.object(self.worker, "preflight", side_effect=Refusal("WORKER_PREFLIGHT_INJECTED")):
            self.refused(lambda: manager.execute("TASK-REQ-READ", "op-read", "dispatcher", self.worker,
                expected_head=original, now=1000), "WORKER_PREFLIGHT_INJECTED")
        self.assertEqual(original, manager.status(expected_head=original, now=1000)["current_head"])
        self.assertFalse((self.base / "outputs/op-read").exists())

    def test_expired_grant_can_only_settle_the_exact_active_ticket(self):
        manager = self.manager()
        started = self.start(manager)
        actions = ["OPEN_RECOVERY", "RECONCILE_NOT_EXECUTED", "STATUS"]
        prepared = manager.prepare_recovery_authorization(started["ticket"],
            expected_head=started["current_head"], actions=actions,
            issued_at=9999, expires_at=10500)
        authorization = authorize_recovery(prepared, provider=self.fixture["provider"],
            signing_handle=self.fixture["issuer_handle"],
            expected_governor=self.fixture["provider"].identity(self.fixture["issuer_handle"]))
        recovered = self.reopen(started["current_head"], now=10000,
                                recovery_authorization=authorization)
        self.assertEqual("RECOVERY_REQUIRED", recovered.status(
            expected_head=started["current_head"], now=10000)["status"])
        attestation = self.worker.attest_not_executed(started["ticket"]["request"])
        settled = recovered.reconcile_not_executed(started["ticket"], attestation,
            expected_head=started["current_head"], now=10000)
        self.assertEqual("PENDING", settled["tasks"]["TASK-REQ-READ"]["state"])
        self.refused(lambda: recovered.execute("TASK-REQ-READ", "new-operation", "dispatcher",
            self.worker, expected_head=settled["current_head"], now=10000),
            "WORKBENCH_CHARTER_EXPIRED_OR_NOT_CURRENT")

    def test_fresh_process_can_prepare_unsigned_recovery_from_pinned_store(self):
        manager = self.manager()
        started = self.start(manager)
        before_state = self.store.path.read_bytes()
        before_journal = self.store.journal_path.read_bytes()
        actions = ["OPEN_RECOVERY", "RECONCILE_NOT_EXECUTED", "STATUS"]
        prepared = WorkbenchManager.prepare_recovery_authorization_offline(
            self.store, project=self.project, plan=self.plan, orientation=self.context,
            orientation_pins=self.fixture["external_pins"],
            worker_identity=self.keys.identity(self.worker_handle),
            worker_root=self.worker.worker_root, ticket=started["ticket"],
            expected_head=started["current_head"], actions=actions,
            issued_at=9999, expires_at=10500)
        self.assertEqual(started["ticket"]["ticket_root"], prepared["ticket_root"])
        self.assertEqual("NONE", prepared["authority_effect"])
        self.assertNotIn("signature", prepared)
        self.assertEqual(before_state, self.store.path.read_bytes())
        self.assertEqual(before_journal, self.store.journal_path.read_bytes())

    def test_offline_recovery_preparation_refuses_stale_head_and_wrong_ticket_without_mutation(self):
        manager = self.manager()
        started = self.start(manager)
        before_state = self.store.path.read_bytes()
        before_journal = self.store.journal_path.read_bytes()
        common = {"project": self.project, "plan": self.plan, "orientation": self.context,
                  "orientation_pins": self.fixture["external_pins"],
                  "worker_identity": self.keys.identity(self.worker_handle),
                  "worker_root": self.worker.worker_root,
                  "actions": ["OPEN_RECOVERY", "RECONCILE_NOT_EXECUTED", "STATUS"],
                  "issued_at": 9999, "expires_at": 10500}
        self.refused(lambda: WorkbenchManager.prepare_recovery_authorization_offline(
            self.store, ticket=started["ticket"], expected_head={"sequence": 0, "head": "GENESIS"},
            **common), "WORKBENCH_STALE_EXTERNAL_HEAD")
        wrong = deepcopy(started["ticket"])
        wrong["dispatcher_id"] = "other-dispatcher"
        wrong["ticket_root"] = root({key: value for key, value in wrong.items() if key != "ticket_root"})
        self.refused(lambda: WorkbenchManager.prepare_recovery_authorization_offline(
            self.store, ticket=wrong, expected_head=started["current_head"], **common),
            "WORKBENCH_ACTIVE_TICKET_MISMATCH")
        self.assertEqual(before_state, self.store.path.read_bytes())
        self.assertEqual(before_journal, self.store.journal_path.read_bytes())

    def test_after_worker_interruption_reconciles_receipt_without_repeat(self):
        manager = self.manager()
        started = self.start(manager)
        actual = self.worker.execute(started["ticket"]["request"])
        reopened = self.reopen(started["current_head"])
        recovered = reopened.complete_dispatch(started["ticket"], actual,
                                               expected_head=started["current_head"], now=1000)
        self.assertEqual("COMPLETE", recovered["tasks"]["TASK-REQ-READ"]["state"])
        self.assertEqual(1, recovered["budget_spent_units"])

    def test_worker_exception_is_uncertain_with_no_blind_retry(self):
        manager = self.manager()
        with patch.object(self.worker, "execute", side_effect=RuntimeError("interrupted")):
            pending = manager.execute("TASK-REQ-READ", "op-read", "dispatcher", self.worker,
                                      expected_head=manager.current_head, now=1000)
        self.assertEqual("UNCERTAIN", pending["tasks"]["TASK-REQ-READ"]["state"])
        self.refused(lambda: self.start(manager, pending["current_head"]), "WORKBENCH_RECONCILIATION_REQUIRED")

    def test_budget_is_recorded_before_work_and_not_asserted(self):
        small = create_plan(self.project, pins=self.pins, task_actions=self.actions, budget_limit_units=1)
        manager = self.manager(plan=small)
        first = manager.execute("TASK-REQ-READ", "op-read", "dispatcher", self.worker,
                                expected_head=manager.current_head, now=1000)
        self.refused(lambda: self.start(manager, first["current_head"], tid="TASK-ART-TARGET", oid="second"),
                     "WORKBENCH_BUDGET_EXCEEDED")

    def test_tenant_and_jurisdiction_context_substitution_refuses(self):
        manager = self.manager()
        altered = build_fixture_orientation(roots={"project": self.project["snapshot_root"],
            "source": self.snapshot["source_root"]}, tenant_id="other-tenant")
        self.refused(lambda: self.reopen(manager.current_head, orientation=altered["context"],
            orientation_pins=altered["external_pins"]), "WORKBENCH_ORIENTATION_PIN_MISMATCH")
        self.refused(lambda: self.reopen(manager.current_head, worker_root=root("other-worker")),
                     "WORKBENCH_WORKER_PIN_MISMATCH")

    def test_changed_and_rolled_back_signed_store_refuse(self):
        manager = self.manager()
        original_state, original_journal = self.store.path.read_bytes(), self.store.journal_path.read_bytes()
        started = self.start(manager)
        advanced_state, advanced_journal = self.store.path.read_bytes(), self.store.journal_path.read_bytes()
        altered = strict_loads(advanced_state)
        altered["body"]["payload"]["generation"] = 2
        self.store.path.write_text(json.dumps(altered), encoding="utf-8")
        self.refused(lambda: self.reopen(started["current_head"]), "SIGNED_BODY_ROOT_MISMATCH")
        self.store.path.write_bytes(original_state); self.store.journal_path.write_bytes(original_journal)
        self.refused(lambda: self.reopen(started["current_head"]), "PROTECTED_STATE_ROLLBACK_OR_AHEAD")
        self.store.path.write_bytes(advanced_state); self.store.journal_path.write_bytes(advanced_journal)

    def test_portable_capsule_same_external_head_import_and_stale_refusal(self):
        manager = self.manager()
        initial = manager.export_capsule(expected_head=manager.current_head, now=1000)
        started = self.start(manager)
        fresh = manager.export_capsule(expected_head=started["current_head"], now=1000)
        destination = ProtectedStateStore(self.base / "imported", anchor=self.anchor,
                                           keys=self.keys, signing_handle=self.state_handle)
        self.refused(lambda: WorkbenchManager.import_capsule(destination, initial,
            expected_head=started["current_head"], **self.args()), "WORKBENCH_CAPSULE_CONTRACT_MISMATCH")
        imported = WorkbenchManager.import_capsule(destination, fresh,
            expected_head=started["current_head"], **self.args())
        self.assertEqual("RECOVERY_REQUIRED", imported.status(expected_head=started["current_head"], now=1000)["status"])
        self.assertEqual(self.store.path.read_bytes(), destination.path.read_bytes())

    def test_interrupted_storage_commit_is_recovered_without_worker(self):
        manager = self.manager()
        previous = dict(manager.current_head)
        ordinary_commit = self.store.commit
        def crashing(payload, **kwargs):
            return ordinary_commit(payload, crash_at="AFTER_JOURNAL", **kwargs)
        with patch.object(self.store, "commit", side_effect=crashing):
            self.refused(lambda: self.start(manager), "SIMULATED_CRASH_AFTER_JOURNAL")
        self.refused(lambda: self.reopen(previous), "PROTECTED_COMMIT_RECOVERY_REQUIRED")
        recovered = WorkbenchManager.reopen_recovering_store(self.store, expected_head=previous, **self.args())
        state = recovered.status(expected_head=recovered.current_head, now=1000)
        self.assertEqual("IN_FLIGHT", state["tasks"]["TASK-REQ-READ"]["state"])
        self.assertFalse((self.base / "outputs/op-read").exists())

    def test_missing_worker_pin_and_expired_context_refuse(self):
        self.refused(lambda: self.manager(worker_root=None), "ROOT_INVALID")
        self.refused(lambda: self.manager(now=10000), "WORKBENCH_CHARTER_EXPIRED_OR_NOT_CURRENT")


if __name__ == "__main__":
    unittest.main()
