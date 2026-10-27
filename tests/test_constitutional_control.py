import json
import os
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from helpers import ROOT
from miw.cli import parser
from miw.common import Refusal, read_json, seal
from miw.constitutional import (
    OBSERVABILITY_LEVELS, capability_surface, cgp_posture, compile_operation,
    diagnose, run_ctr, validate_operation_registry,
)
from miw.foundry_view import payload
from miw.headless_runner import HeadlessRunner, application_court
from miw.workbench import build_workspace


class ConstitutionalControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = read_json(ROOT / 'constitutional/OPERATION-REGISTRY.json')
        cls.plan = read_json(ROOT / 'constitutional/CTR-PLAN.json')
        cls.dossier = ROOT / 'evidence/invariant-workbench-demo-v8'
        cls.bindings = ROOT / 'examples/assembly/workbench.bindings.json'

    def test_closed_registry_covers_every_cli_and_ui_operation(self):
        cli = list(parser()._subparsers._group_actions[0].choices)
        ui = payload()['application']['declared_operation_ids']
        checked = validate_operation_registry(self.registry, cli_operations=cli, ui_operations=ui)
        self.assertEqual(checked['status'], 'PASSED')

    def test_capability_surface_is_zero_authority(self):
        surface = capability_surface(self.registry)
        self.assertEqual(surface['authority_effect'], 'NONE')
        self.assertEqual(surface['mutation_authority'], 'NONE')
        self.assertEqual(surface['observability_levels'], ['SENTINEL', 'RECEIPT', 'DIAGNOSTIC'])

    def test_operation_compiler_keeps_five_commitments_independent(self):
        compiled = compile_operation(self.registry, 'workbench-open',
                                     subject={'dossier_root': 'a' * 64}, inputs={}, requester='TEST')
        self.assertEqual(set(compiled['commitments']), {'h_s', 'h_c', 'h_m', 'h_j', 'h_r'})
        self.assertEqual(len(set(compiled['commitments'].values())), 5)
        self.assertEqual(compiled['execution_authority'], 'NOT_GRANTED_BY_PLAN')

    def test_unknown_operation_refuses(self):
        with self.assertRaisesRegex(Refusal, 'CONTROL_OPERATION_UNDECLARED'):
            compile_operation(self.registry, 'repair-everything', subject={}, inputs={})

    def test_external_effects_are_explicit(self):
        external = {'LOOPBACK_REQUEST', 'TRUSTED_LOCAL_PROCESS', 'DISPOSABLE_DATABASE', 'COMPILER_EXECUTION'}
        for row in self.registry['operations']:
            if row['effect_class'] in external:
                self.assertIn(row['admission'], {'EXPLICIT_OPT_IN', 'EXTERNAL_GATE'})

    def test_headless_runner_refuses_shell(self):
        with self.assertRaisesRegex(Refusal, 'HEADLESS_SHELL_FORBIDDEN'):
            HeadlessRunner().run(['helper'], shell=True)

    # Host-neutral: the runner reads os.name and subprocess.* through its own
    # module globals, so both branches are exercised on every host by replacing
    # those two module attributes. Global os/subprocess are never mutated. On
    # Windows the same court also exercises CPython's real console constants and
    # STARTUPINFO wiring while process creation remains mocked.
    @staticmethod
    def _fake_subprocess(completed):
        class FakeStartupInfo:
            def __init__(self):
                self.dwFlags = 0
                self.wShowWindow = None
        return mock.Mock(
            spec=['run', 'CREATE_NO_WINDOW', 'STARTUPINFO', 'STARTF_USESHOWWINDOW', 'SW_HIDE'],
            run=mock.Mock(return_value=completed), CREATE_NO_WINDOW=0x08000000,
            STARTUPINFO=FakeStartupInfo, STARTF_USESHOWWINDOW=0x00000001, SW_HIDE=0)

    def test_headless_runner_suppresses_windows_console(self):
        completed = mock.Mock(returncode=0)
        fake = self._fake_subprocess(completed)
        with mock.patch('miw.headless_runner.os', mock.Mock(spec=['name'], name='os')) as fake_os, \
                mock.patch('miw.headless_runner.subprocess', fake):
            fake_os.name = 'nt'
            self.assertIs(HeadlessRunner().run(['helper.exe'], check=False), completed)
        args, kwargs = fake.run.call_args
        self.assertEqual(args, (['helper.exe'],))
        self.assertIs(kwargs['shell'], False)
        self.assertTrue(kwargs['creationflags'] & fake.CREATE_NO_WINDOW)
        self.assertTrue(kwargs['startupinfo'].dwFlags & fake.STARTF_USESHOWWINDOW)
        self.assertEqual(kwargs['startupinfo'].wShowWindow, fake.SW_HIDE)

        if os.name == 'nt':
            native_completed = mock.Mock(returncode=0)
            with mock.patch('miw.headless_runner.subprocess.run',
                            return_value=native_completed) as native_run:
                self.assertIs(HeadlessRunner().run(['helper.exe'], check=False),
                              native_completed)
            native_args, native_kwargs = native_run.call_args
            self.assertEqual(native_args, (['helper.exe'],))
            self.assertIs(native_kwargs['shell'], False)
            self.assertTrue(native_kwargs['creationflags'] & subprocess.CREATE_NO_WINDOW)
            self.assertTrue(native_kwargs['startupinfo'].dwFlags & subprocess.STARTF_USESHOWWINDOW)
            self.assertEqual(native_kwargs['startupinfo'].wShowWindow, subprocess.SW_HIDE)

    def test_headless_runner_adds_no_console_flags_off_windows(self):
        completed = mock.Mock(returncode=0)
        fake = self._fake_subprocess(completed)
        with mock.patch('miw.headless_runner.os', mock.Mock(spec=['name'], name='os')) as fake_os, \
                mock.patch('miw.headless_runner.subprocess', fake):
            fake_os.name = 'posix'
            self.assertIs(HeadlessRunner().run(['helper'], check=False), completed)
        args, kwargs = fake.run.call_args
        self.assertEqual(args, (['helper'],))
        self.assertEqual(kwargs, {'shell': False, 'check': False})

    def test_real_semantic_application_court(self):
        report = application_court(self.dossier, self.bindings)
        self.assertEqual(report['status'], 'PASSED_HEADLESS_APPLICATION_COURT')
        self.assertEqual(report['workbench_flow']['run'], 'LOCAL CHECK CHECKED_SOURCE_PROOF')
        self.assertEqual(report['native_window_execution'], 'NOT_ESTABLISHED_BY_HEADLESS_RUNNER')

    def test_mosaic_control_surface_compiles_and_diagnoses_without_repair(self):
        from miw.foundry_view import make_headless
        ui = make_headless(self.dossier)
        controller = ui.miw_controller
        controller.dispatch({'intent':'ACTIVATE','node_id':'nav_control'})
        controller.dispatch({'intent':'ACTIVATE','node_id':'control_refresh'})
        self.assertEqual(ui.state['status'], 'CAPABILITY SURFACE VALIDATED')
        controller.dispatch({'intent':'ACTIVATE','node_id':'control_compile'})
        self.assertEqual(ui.state['status'], 'OPERATION COMPILED | NO AUTHORITY')
        controller.dispatch({'intent':'ACTIVATE','node_id':'control_diagnose'})
        self.assertEqual(ui.state['status'], 'DIAGNOSTIC COMPLETE | NO REPAIR EFFECT')

    def test_cgp_posture_and_diagnostic_preserve_gaps(self):
        workspace = build_workspace(self.dossier, read_json(self.bindings))
        proof = seal({'schema':'miw.workbench-local-execution.v1','outcome':'CHECKED_SOURCE_PROOF'},
                     'execution_receipt_root')
        bdd = seal({'schema':'miw.workbench-local-execution.v1','outcome':'PASSED'},
                   'execution_receipt_root')
        headless = application_court(self.dossier, self.bindings)
        posture = cgp_posture(self.registry, workspace, proof, bdd, headless)
        self.assertEqual(posture['axes']['EVS']['status'], 'PROVEN')
        self.assertEqual(posture['axes']['SRSA']['status'], 'GAP')
        diagnostic = diagnose(posture)
        self.assertEqual(diagnostic['repair_effect'], 'NONE')
        self.assertTrue(any(row['axis'] == 'SRSA' for row in diagnostic['actions']))

    def test_ctr_covers_declared_courts(self):
        report = run_ctr(self.plan, self.registry, ROOT, self.dossier, self.bindings)
        self.assertEqual(report['status'], 'PASSED')
        self.assertEqual(report['coverage'], {'declared': 9, 'passed': 9})

    def test_observability_levels_are_exact(self):
        self.assertEqual(OBSERVABILITY_LEVELS, ('SENTINEL', 'RECEIPT', 'DIAGNOSTIC'))


if __name__ == '__main__':
    unittest.main()
