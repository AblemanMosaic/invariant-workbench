from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from uclop.canonical import root
from uclop.custody import OpaqueEd25519KeyStore
from uclop.protected_state import InMemoryMonotonicAnchor, ProtectedStateStore
from uclop.workbench_manager import WorkbenchManager, create_plan
from uclop.workbench_migration import (MIGRATION_DOMAIN, authorize_migration, migrate,
                                      prepare_migration, resume_migration, verify_predecessor)
from uclop.workbench_orientation import build_fixture_orientation
from uclop.workbench_workers import BoundedWorker, snapshot_source
from tests import test_workbench_manager as manager_tests
project_for = manager_tests.project_for


class WorkbenchMigrationTests(unittest.TestCase):
    setUp = manager_tests.WorkbenchManagerTests.setUp
    args = manager_tests.WorkbenchManagerTests.args
    manager = manager_tests.WorkbenchManagerTests.manager
    refused = manager_tests.WorkbenchManagerTests.refused
    start = manager_tests.WorkbenchManagerTests.start

    def target(self, generation=2, *, tenant="fixture-tenant", project_id=None):
        source = self.base / ("source-" + str(generation))
        shutil.copytree(self.source, source)
        (source / "README.txt").write_text("generation-" + str(generation), encoding="utf-8")
        snapshot = snapshot_source(source)
        project = project_for(snapshot["source_root"])
        if project_id is not None:
            project["project_id"] = project_id
            from uclop import project_intelligence as pi
            project["snapshot_root"] = pi.rooted({k: v for k, v in project.items() if k != "snapshot_root"})
        fixture = build_fixture_orientation(nonce_label="successor-" + str(generation), tenant_id=tenant,
            roots={"project": project["snapshot_root"], "source": snapshot["source_root"]})
        context = fixture["context"]
        pins = {name: context[name] for name in self.pins}
        actions = deepcopy(self.actions)
        actions["ART-TARGET"] = {"operation": "INSPECT_ARTIFACTS", "payload": {"paths": ["README.txt"]}}
        actions["VER-REAL"] = {"operation": "RUN_TESTS", "payload": {"modules": ["tests.test_sample"]}}
        plan = create_plan(project, pins=pins, task_actions=actions)
        state_handle = self.keys.install_fixture_seed("WITNESS", bytes([120 + generation]) * 32, generation=generation)
        worker_handle = self.keys.install_fixture_seed("NODE", bytes([150 + generation]) * 32, generation=generation)
        store = ProtectedStateStore(self.base / ("state-" + str(generation)), anchor=InMemoryMonotonicAnchor(),
                                   keys=self.keys, signing_handle=state_handle)
        worker = BoundedWorker(source_directory=source, source_manifest=snapshot,
            output_directory=self.base / ("outputs-" + str(generation)), bindings=pins,
            tenant_id=context["tenant_id"], provider=self.keys, signing_handle=worker_handle,
            expected_issuer=self.keys.identity(worker_handle), trusted_tests={},
            maximum_artifact_bytes=context["budgets"]["max_artifact_bytes"])
        args = {"project": project, "plan": plan, "orientation": context,
                "orientation_pins": fixture["external_pins"], "worker_identity": self.keys.identity(worker_handle),
                "worker_root": worker.worker_root}
        return {"store": store, "worker": worker, "fixture": fixture, "args": args}

    def prepare(self, manager, target, head=None):
        args = target["args"]
        return prepare_migration(manager, expected_head=head or manager.current_head, now=1000,
            target_project=args["project"], target_plan=args["plan"], target_orientation=args["orientation"],
            target_orientation_pins=args["orientation_pins"], target_state_identity=target["store"].identity,
            target_worker_identity=args["worker_identity"], target_worker_root=args["worker_root"])

    def authorize(self, prepared):
        return authorize_migration(prepared, provider=self.fixture["provider"],
            signing_handle=self.fixture["issuer_handle"],
            expected_governor=self.fixture["provider"].identity(self.fixture["issuer_handle"]))

    def migrate(self, manager, target, prepared=None, authorization=None, old_head=None, now=1000):
        prepared = prepared or self.prepare(manager, target)
        authorization = authorization or self.authorize(prepared)
        return migrate(manager, target["store"], prepared=prepared, authorization=authorization,
            expected_old_head=old_head or manager.current_head,
            expected_new_head={"sequence": 0, "head": "GENESIS"}, now=now, **target["args"])

    def test_signed_preparation_time_is_stable_across_later_execution(self):
        manager, target = self.manager(), self.target()
        prepared = self.prepare(manager, target)
        successor = self.migrate(manager, target, prepared=prepared,
                                 authorization=self.authorize(prepared), now=1001)
        self.assertEqual(2, target["store"].load()["body"]["payload"]["generation"])
        self.assertEqual("WORK_PENDING", successor.status(expected_head=successor.current_head, now=1001)["status"])

    def test_migration_before_signed_preparation_time_refuses(self):
        manager, target = self.manager(), self.target()
        prepared = self.prepare(manager, target)
        self.refused(lambda: self.migrate(manager, target, prepared=prepared,
            authorization=self.authorize(prepared), now=999),
            "WORKBENCH_MIGRATION_AUTHORIZATION_TIME_INVALID")

    def test_signed_changed_source_successor_preserves_history_not_completion(self):
        manager = self.manager()
        completed = manager.execute("TASK-REQ-READ", "old-read", "dispatcher", self.worker,
                                    expected_head=manager.current_head, now=1000)
        target = self.target()
        prepared = self.prepare(manager, target)
        self.assertEqual(1, len(prepared["body"]["source"]["accepted_receipts"]))
        self.assertEqual(2, len(prepared["body"]["source"]["pending_tasks"]))
        successor = self.migrate(manager, target, prepared=prepared)
        record = target["store"].load()["body"]["payload"]
        self.assertEqual(2, record["generation"])
        self.assertIsNotNone(record["predecessor"])
        status = successor.status(expected_head=successor.current_head, now=1000)
        self.assertTrue(all(row["state"] == "PENDING" for row in status["tasks"].values()))
        self.assertEqual(0, status["budget_spent_units"])
        self.assertEqual([], status["project_obligations_satisfied"])
        self.assertNotEqual(self.snapshot["source_root"], successor.pins["source_root"])

    def test_old_store_is_terminal_and_same_generation_fork_refuses(self):
        manager = self.manager()
        target = self.target()
        old_head = dict(manager.current_head)
        prepared = self.prepare(manager, target)
        authorization = self.authorize(prepared)
        successor = self.migrate(manager, target, prepared, authorization)
        sequence, head = self.store.anchor.observe()
        self.refused(lambda: manager.status(expected_head={"sequence": sequence, "head": head}, now=1000),
                     "WORKBENCH_SUCCESSOR_ALREADY_BOUND")
        self.refused(lambda: self.migrate(manager, target, prepared, authorization, old_head),
                     "WORKBENCH_STALE_EXTERNAL_HEAD")
        self.assertEqual(1, successor.current_head["sequence"])

    def test_stale_old_pin_refuses_before_migration(self):
        manager = self.manager()
        old = dict(manager.current_head)
        manager.execute("TASK-REQ-READ", "old-read", "dispatcher", self.worker,
                        expected_head=old, now=1000)
        target = self.target()
        self.refused(lambda: self.prepare(manager, target, old), "WORKBENCH_STALE_EXTERNAL_HEAD")

    def test_in_flight_and_uncertain_source_cannot_migrate(self):
        manager = self.manager()
        started = self.start(manager)
        target = self.target()
        self.refused(lambda: self.prepare(manager, target, started["current_head"]), "WORKBENCH_MIGRATION_IN_FLIGHT")
        uncertain = manager.mark_uncertain(started["ticket"], diagnostic="INTERRUPTED",
                                            expected_head=started["current_head"], now=1000)
        self.refused(lambda: self.prepare(manager, target, uncertain["current_head"]), "WORKBENCH_MIGRATION_IN_FLIGHT")

    def test_wrong_governor_signature_is_refused(self):
        manager, target = self.manager(), self.target()
        prepared = self.prepare(manager, target)
        attacker = OpaqueEd25519KeyStore()
        handle = attacker.install_fixture_seed("GOVERNOR", b"X" * 32)
        signed = attacker.sign(handle, MIGRATION_DOMAIN, prepared["body"])
        self.refused(lambda: self.migrate(manager, target, prepared, signed), "SIGNATURE_KEY_ROOT_MISMATCH")

    def test_wrong_project_and_tenant_refuse(self):
        manager, target = self.manager(), self.target(project_id="OTHER-PROJECT")
        self.refused(lambda: self.prepare(manager, target), "WORKBENCH_MIGRATION_PROJECT_MISMATCH")
        # A separate key generation for this otherwise valid target fixture.
        target = self.target(3, tenant="other-tenant")
        self.refused(lambda: self.prepare(manager, target), "WORKBENCH_MIGRATION_TENANT_MISMATCH")

    def test_missing_or_added_accepted_receipts_refuse(self):
        manager = self.manager()
        manager.execute("TASK-REQ-READ", "old-read", "dispatcher", self.worker,
                        expected_head=manager.current_head, now=1000)
        target = self.target()
        prepared = self.prepare(manager, target)
        for rows in ([], prepared["body"]["source"]["accepted_receipts"] * 2):
            altered = deepcopy(prepared)
            altered["body"]["source"]["accepted_receipts"] = rows
            signed = self.authorize(altered)
            self.refused(lambda: self.migrate(manager, target, prepared, signed), "WORKBENCH_MIGRATION_AUTHORIZATION_MISMATCH")

    def test_reused_generation_or_substituted_target_refuse(self):
        manager, target = self.manager(), self.target()
        prepared = self.prepare(manager, target)
        changed = deepcopy(prepared)
        changed["body"]["target"]["generation"] = 1
        self.refused(lambda: self.migrate(manager, target, prepared, self.authorize(changed)),
                     "WORKBENCH_MIGRATION_GENERATION_INVALID")
        changed = deepcopy(prepared)
        changed["body"]["target"]["pins"]["source_root"] = root("other-source")
        self.refused(lambda: self.migrate(manager, target, prepared, self.authorize(changed)),
                     "WORKBENCH_MIGRATION_AUTHORIZATION_MISMATCH")

    def test_interrupted_child_commit_resumes_without_resetting_old_custody(self):
        manager, target = self.manager(), self.target()
        prepared = self.prepare(manager, target)
        authorization = self.authorize(prepared)
        original = target["store"].commit
        def interrupted(payload, **kwargs):
            return original(payload, crash_at="AFTER_JOURNAL", **kwargs)
        with patch.object(target["store"], "commit", side_effect=interrupted):
            self.refused(lambda: self.migrate(manager, target, prepared, authorization), "SIMULATED_CRASH_AFTER_JOURNAL")
        sequence, head = self.store.anchor.observe()
        successor = resume_migration(self.store, target["store"],
            expected_old_head={"sequence": sequence, "head": head},
            expected_new_head={"sequence": 0, "head": "GENESIS"}, now=1000, **target["args"])
        self.assertEqual(2, target["store"].load()["body"]["payload"]["generation"])
        self.assertEqual("WORK_PENDING", successor.status(expected_head=successor.current_head, now=1000)["status"])

    def test_interrupted_source_terminal_commit_is_reconciled_exactly(self):
        manager, target = self.manager(), self.target()
        prepared = self.prepare(manager, target)
        authorization = self.authorize(prepared)
        original, source_head = self.store.commit, dict(manager.current_head)
        def interrupted(payload, **kwargs):
            return original(payload, crash_at="AFTER_JOURNAL", **kwargs)
        with patch.object(self.store, "commit", side_effect=interrupted):
            self.refused(lambda: self.migrate(manager, target, prepared, authorization), "SIMULATED_CRASH_AFTER_JOURNAL")
        successor = resume_migration(self.store, target["store"], expected_old_head=source_head,
            expected_new_head={"sequence": 0, "head": "GENESIS"}, now=1000, **target["args"])
        self.assertEqual(2, target["store"].load()["body"]["payload"]["generation"])
        self.assertEqual("WORK_PENDING", successor.status(expected_head=successor.current_head, now=1000)["status"])

    def test_bad_target_configuration_refuses_before_consuming_source(self):
        manager, target = self.manager(), self.target()
        original = dict(manager.current_head)
        bad = build_fixture_orientation(roots={"project": target["args"]["project"]["snapshot_root"],
            "source": target["args"]["plan"]["pins"]["source_root"], "registry": root("wrong-registry")})
        target["args"]["orientation"], target["args"]["orientation_pins"] = bad["context"], bad["external_pins"]
        self.refused(lambda: self.prepare(manager, target), "WORKBENCH_ORIENTATION_PIN_MISMATCH")
        self.assertEqual(original, manager.status(expected_head=original, now=1000)["current_head"])

    def test_successor_capsule_can_move_with_predecessor_chain(self):
        manager, target = self.manager(), self.target()
        successor = self.migrate(manager, target)
        capsule = successor.export_capsule(expected_head=successor.current_head, now=1000)
        imported_store = ProtectedStateStore(self.base / "successor-import", anchor=target["store"].anchor,
            keys=self.keys, signing_handle=target["store"].signing_handle)
        imported = WorkbenchManager.import_capsule(imported_store, capsule,
            expected_head=successor.current_head, now=1000, **target["args"])
        self.assertEqual(successor.current_head, imported.current_head)
        self.assertEqual(target["store"].path.read_bytes(), imported_store.path.read_bytes())

    def test_second_successor_verifies_complete_predecessor_chain(self):
        first, target = self.manager(), self.target()
        second = self.migrate(first, target)
        third_target = self.target(3)
        third = self.migrate(second, third_target)
        payload = third_target["store"].load()["body"]["payload"]
        self.assertEqual(3, payload["generation"])
        prior = payload["predecessor"]["source_capsule"]["body"]["state_record"]["body"]["payload"]
        self.assertEqual(2, prior["generation"])
        self.assertIsNotNone(prior["predecessor"])
        self.assertEqual("WORK_PENDING", third.status(expected_head=third.current_head, now=1000)["status"])

    def test_documented_six_generation_boundary_is_executable(self):
        manager = self.manager()
        for generation in range(2, 7):
            target = self.target(generation)
            manager = self.migrate(manager, target)
        self.assertEqual(6, target["store"].load()["body"]["payload"]["generation"])
        self.assertEqual("WORK_PENDING", manager.status(expected_head=manager.current_head, now=1000)["status"])
        seventh = self.target(7)
        self.refused(lambda: self.prepare(manager, seventh), "WORKBENCH_MIGRATION_GENERATION_INVALID")


if __name__ == "__main__":
    unittest.main()
