"""Reconstruction regressions. Windows metadata is simulated unless on Windows.

These do not replace a real Windows consolidated replay or HWND acceptance.
"""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
from helpers import ROOT,directory_alias
from miw.common import Refusal, read_bytes, validate_replay_output, _assert_read_stability


def observation(**changes):
    data = dict(st_dev=17, st_ino=31, st_size=7, st_mtime_ns=123456789,
                st_mode=stat.S_IFREG | 0o666)
    data.update(changes)
    return SimpleNamespace(**data)


class ReadMetadataReconstructionTests(unittest.TestCase):
    def check(self, *, windows=True, name='RUN_MIW.bat', before=None,
              opened=None, after_fd=None, after_path=None):
        opened = opened or observation()
        before = before or observation(st_mode=stat.S_IFREG | 0o777)
        with patch('miw.common._WINDOWS_STAT_EXECUTE_COMPAT', windows):
            _assert_read_stability(Path(name), before, opened,
                                   after_fd or opened, after_path or before)

    def test_windows_batch_path_handle_execute_bits_accepted(self):
        self.check()

    def test_posix_does_not_ignore_execute_permissions(self):
        with self.assertRaisesRegex(Refusal, 'FILE_CHANGED_DURING_READ'):
            self.check(windows=False)

    def test_same_full_metadata_is_accepted_on_posix(self):
        self.check(windows=False, before=observation())

    def test_uppercase_windows_extension_is_accepted(self):
        self.check(name='RUN_MIW.BAT')

    def test_other_cpython_executable_suffixes_accepted(self):
        for suffix in ('.cmd', '.exe', '.com'):
            with self.subTest(suffix=suffix):
                self.check(name='tool'+suffix)

    def test_nonexecutable_suffix_does_not_relax_mode(self):
        with self.assertRaises(Refusal):
            self.check(name='requirements.txt')

    def test_permission_write_bit_difference_refused(self):
        with self.assertRaises(Refusal):
            self.check(before=observation(st_mode=stat.S_IFREG | 0o755))

    def test_permission_read_bit_difference_refused(self):
        with self.assertRaises(Refusal):
            self.check(before=observation(st_mode=stat.S_IFREG | 0o733))

    def test_path_mode_change_during_read_refused(self):
        with self.assertRaises(Refusal):
            self.check(after_path=observation())

    def test_handle_mode_change_during_read_refused(self):
        with self.assertRaises(Refusal):
            self.check(after_fd=observation(st_mode=stat.S_IFREG | 0o777))

    def test_reverse_execute_bit_difference_refused(self):
        with self.assertRaises(Refusal):
            self.check(before=observation(), opened=observation(st_mode=stat.S_IFREG | 0o777))

    def test_device_replacement_refused(self):
        with self.assertRaises(Refusal):
            self.check(opened=observation(st_dev=18))

    def test_inode_replacement_refused(self):
        with self.assertRaises(Refusal):
            self.check(opened=observation(st_ino=32))

    def test_size_difference_refused(self):
        with self.assertRaises(Refusal):
            self.check(opened=observation(st_size=8))

    def test_timestamp_difference_refused(self):
        with self.assertRaises(Refusal):
            self.check(opened=observation(st_mtime_ns=123456790))

    def test_handle_changes_during_read_refused(self):
        with self.assertRaises(Refusal):
            self.check(after_fd=observation(st_size=8))

    def test_path_replaced_by_symlink_refused(self):
        with self.assertRaises(Refusal):
            self.check(after_path=observation(st_mode=stat.S_IFLNK | 0o777))

    def test_open_handle_must_be_regular(self):
        with self.assertRaises(Refusal):
            self.check(opened=observation(st_mode=stat.S_IFDIR | 0o666))

    def test_real_batch_file_read_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'RUN_MIW.bat'
            path.write_bytes(b'echo ok')
            self.assertEqual(read_bytes(path), b'echo ok')

    def test_read_bytes_accepts_simulated_windows_stat_disagreement(self):
        # Real file content and handle, simulated metadata; not Windows evidence.
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'RUN_MIW.bat'
            path.write_bytes(b'echo ok')
            real = path.stat()
            handle = observation(st_dev=real.st_dev, st_ino=real.st_ino,
                                 st_mtime_ns=real.st_mtime_ns)
            named = observation(**{**vars(handle), 'st_mode': stat.S_IFREG | 0o777})
            with patch('miw.common._WINDOWS_STAT_EXECUTE_COMPAT', True), \
                 patch.object(type(path), 'lstat', return_value=named), \
                 patch('miw.common.os.fstat', return_value=handle):
                self.assertEqual(read_bytes(path), b'echo ok')

    def test_read_bytes_still_refuses_replaced_open_handle(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'RUN_MIW.bat'; path.write_bytes(b'echo ok')
            named=observation(st_mode=stat.S_IFREG | 0o777)
            with patch('miw.common._WINDOWS_STAT_EXECUTE_COMPAT', True), \
                 patch.object(type(path), 'lstat', return_value=named), \
                 patch('miw.common.os.fstat', return_value=observation(st_ino=999)):
                with self.assertRaisesRegex(Refusal, 'FILE_REPLACED_DURING_READ'):
                    read_bytes(path)


class ReplayPathReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.base=Path(self.temporary.name); self.project=self.base/'project'
        self.project.mkdir(); (self.project/'evidence').mkdir()

    def helper_refuses(self, tool, traversal=False):
        spec=importlib.util.spec_from_file_location('reconstructed_'+tool, ROOT/'tools'/tool)
        mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        mod.ROOT=self.project
        out=self.project/('evidence/../pollution' if traversal else 'pollution')
        argv=[tool, '--out', str(out)]
        if tool=='reproduce_turn3_findings.py': argv.append('--allow-reviewed-subject')
        with patch.object(sys, 'argv', argv), \
             patch.object(mod.subprocess, 'run', side_effect=AssertionError('must refuse before running')):
            with self.assertRaisesRegex(Refusal, 'OUTPUT_INSIDE_SOURCE_INVENTORY'):
                mod.main()
        self.assertEqual(sorted(p.name for p in self.project.iterdir()), ['evidence'])
        self.assertFalse((self.project/'pollution').exists())

    def test_replay_helper_refuses_source_output_before_mutation(self):
        self.helper_refuses('replay_turn4.py')

    def test_replay_helper_refuses_dotdot_source_output_before_mutation(self):
        self.helper_refuses('replay_turn4.py', traversal=True)

    def test_findings_helper_refuses_source_output_before_mutation(self):
        self.helper_refuses('reproduce_turn3_findings.py')

    def test_findings_helper_refuses_dotdot_source_output_before_mutation(self):
        self.helper_refuses('reproduce_turn3_findings.py', traversal=True)

    def test_output_under_evidence_allowed_without_creating_it(self):
        output=self.project/'evidence/new/run'
        self.assertEqual(validate_replay_output(self.project, output), output.resolve())
        self.assertFalse(output.exists())

    def test_output_outside_project_allowed_without_creating_it(self):
        output=self.base/'results'
        self.assertEqual(validate_replay_output(self.project, output), output.resolve())
        self.assertFalse(output.exists())

    def test_evidence_prefix_is_not_evidence_directory(self):
        with self.assertRaisesRegex(Refusal, 'OUTPUT_INSIDE_SOURCE_INVENTORY'):
            validate_replay_output(self.project, self.project/'evidence-looks-safe/new')

    def test_existing_output_refused(self):
        with self.assertRaises(Refusal):
            validate_replay_output(self.project, self.project/'evidence')

    def test_normalized_evidence_output_accepted(self):
        output=self.project/'evidence/temp/../new'
        self.assertEqual(validate_replay_output(self.project, output), self.project/'evidence/new')
        self.assertFalse((self.project/'evidence/temp').exists())

    def test_symlink_evidence_ancestor_refused_before_normalization(self):
        alias=self.base/'alias'; directory_alias(alias,self.project/'evidence')
        with self.assertRaises(Refusal):
            validate_replay_output(self.project, alias/'new')
        self.assertFalse((self.project/'evidence/new').exists())

    def test_symlink_then_dotdot_not_normalized_away(self):
        alias=self.project/'evidence/alias'; directory_alias(alias,self.base)
        with self.assertRaises(Refusal):
            validate_replay_output(self.project, alias/'../new')

    def test_missing_evidence_directory_root_itself_refused(self):
        (self.project/'evidence').rmdir()
        with self.assertRaisesRegex(Refusal, 'OUTPUT_INSIDE_SOURCE_INVENTORY'):
            validate_replay_output(self.project, self.project/'evidence')
