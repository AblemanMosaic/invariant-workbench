import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from miw.common import Refusal,read_json
from miw.external_build import preflight,run_zucchini,run_command
from miw.live_postgres import run_live
from miw.cpp_probe import run_probe
from miw.governance import snapshot
from miw.cli import parser
from miw.lifecycle import MemoryRepository
from helpers import ROOT

class ExternalBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.base=Path(self.t.name)
        self.source=self.base/'source';self.source.mkdir();(self.source/'CMakeLists.txt').write_text('# Test fixture only\n')
        self.pin=snapshot(self.source)['snapshot_root'];self.commit='f'*40;self.out=self.base/'out'
    def run_zucchini(self,**kwargs):
        return run_zucchini(self.source,self.out,expected_source_root=self.pin,
                            upstream_commit=self.commit,**kwargs)
    def test_preflight_is_not_execution(self):
        with patch('subprocess.Popen') as popen:
            r=preflight();self.assertEqual(r['postgres_live'],'NOT_RUN');popen.assert_not_called()
    def test_zucchini_denies_implicit_execution(self):
        with patch('subprocess.Popen') as popen:
            with self.assertRaises(Refusal):self.run_zucchini()
            popen.assert_not_called()
    def test_zucchini_wrong_pin_refused(self):
        with self.assertRaises(Refusal):run_zucchini(self.source,self.out,expected_source_root='0'*64,upstream_commit=self.commit,allow_trusted_build=True)
    def test_zucchini_source_nested_output_refused(self):
        with self.assertRaises(Refusal):run_zucchini(self.source,self.source/'build',expected_source_root=self.pin,upstream_commit=self.commit,allow_trusted_build=True)
    def test_zucchini_existing_output_refused(self):
        self.out.mkdir()
        with self.assertRaises(Refusal):self.run_zucchini(allow_trusted_build=True)
    def test_missing_cmake_refused(self):
        with patch('miw.external_build.shutil.which',return_value=None):
            with self.assertRaises(Refusal):self.run_zucchini(allow_trusted_build=True)
    def test_failed_build_recorded_not_passed(self):
        with patch('miw.external_build.shutil.which',return_value='/fixture/tool'),patch('miw.external_build.run_command',return_value={'returncode':1}):
            r=self.run_zucchini(allow_trusted_build=True)
        self.assertEqual(r['status'],'BUILD_INCOMPLETE');self.assertEqual(len(r['commands']),1);self.assertFalse(r['proof_claim'])
    def test_source_edit_during_build_refuses(self):
        def mutation(*a,**kw):(self.source/'CMakeLists.txt').write_text('changed');return {'returncode':1}
        with patch('miw.external_build.shutil.which',return_value='/fixture/tool'),patch('miw.external_build.run_command',side_effect=mutation):
            with self.assertRaises(Refusal):self.run_zucchini(allow_trusted_build=True)
    def test_build_configuration_and_local_dependencies_are_explicit(self):
        calls=[]
        def observed(argv,*args,**kwargs):calls.append(argv);return {'returncode':1}
        definitions=['MIW_CPM_MODULE=/deps/cpm/CPM.cmake','ZUCCHINI_FETCH_TPP=OFF',
                     'ZUCCHINI_NLOHMANN_JSON_SOURCE_DIR=/deps/json','ZUCCHINI_TPP_BIN_DIR=/tools/tpp/bin']
        with patch('miw.external_build.shutil.which',return_value='/fixture/tool'),patch('miw.external_build.run_command',side_effect=observed):
            self.run_zucchini(build_config='Debug',generator='Ninja',cmake_definitions=definitions,allow_trusted_build=True)
        self.assertIn('-DCMAKE_BUILD_TYPE=Debug',calls[0]);self.assertIn('-G',calls[0]);self.assertIn('Ninja',calls[0])
        self.assertIn('-DZUCCHINI_NLOHMANN_JSON_SOURCE_DIR=/deps/json',calls[0])
        self.assertIn('-DMIW_CPM_MODULE=/deps/cpm/CPM.cmake',calls[0])
        self.assertIn('-DZUCCHINI_FETCH_TPP=OFF',calls[0]);self.assertIn('-DZUCCHINI_TPP_BIN_DIR=/tools/tpp/bin',calls[0])
    def test_unknown_cmake_definition_refused_before_execution(self):
        with patch('subprocess.Popen') as popen:
            with self.assertRaises(Refusal):self.run_zucchini(cmake_definitions=['CMAKE_CXX_FLAGS=-include malware'],allow_trusted_build=True)
            popen.assert_not_called()
    def test_commit_pin_is_mandatory_and_lowercase(self):
        with self.assertRaises(Refusal):
            run_zucchini(self.source,self.out,expected_source_root=self.pin,upstream_commit='main',allow_trusted_build=True)
    def test_run_command_actual_local_interpreter(self):
        r=run_command([sys.executable,'-I','-B','-c','print("bounded probe")'],self.base,self.base/'run.log',timeout=10)
        self.assertEqual(r['returncode'],0);self.assertEqual((self.base/'run.log').read_text().strip(),'bounded probe')
    def test_run_command_timeout_bound(self):
        with self.assertRaises(Refusal):run_command([sys.executable],self.base,self.base/'log',timeout=0)
    def test_pg_requires_explicit_admission(self):
        with self.assertRaises(Refusal):run_live(self.out)
    def test_pg_missing_dsn_is_not_run(self):
        with patch.dict('os.environ',{},clear=True):r=run_live(self.out,allow_disposable_database=True)
        self.assertEqual(r['status'],'NOT_RUN');self.assertEqual(r['passed_cases'],0);self.assertFalse(r['live_postgres'])
    def test_pg_never_overwrites_output(self):
        self.out.mkdir()
        with self.assertRaises(Refusal):run_live(self.out,allow_disposable_database=True)
    def test_cpp_probe_requires_admission(self):
        with self.assertRaises(Refusal):run_probe(ROOT,self.out)
    def test_cpp_missing_compiler_not_pass(self):
        with patch('miw.cpp_probe.shutil.which',return_value=None):r=run_probe(ROOT,self.out,allow_trusted_compile=True)
        self.assertEqual(r['status'],'NOT_RUN');self.assertFalse(r['upstream_zucchini'])
    def test_invalid_empty_state_not_defaulted(self):
        with self.assertRaises(Refusal):MemoryRepository(state={})
    def test_native_gui_is_explicit(self):
        args=parser().parse_args(['gui','--directory','demo']);self.assertEqual(args.command,'gui')
    def test_new_cli_routes_available(self):
        for cmd in ('preflight','lifecycle-demo','explore-lifecycle','headless-ui'):
            self.assertEqual(parser().parse_args([cmd]).command,cmd)
    def test_model_cli_defaults_to_no_permission(self):
        args=parser().parse_args(['ollama-propose','--request','x','--model','m','--out','r']);self.assertFalse(args.allow_local_model)
    def test_pg_cli_defaults_to_no_permission(self):
        args=parser().parse_args(['postgres-live','--out','x']);self.assertFalse(args.allow_disposable_database)
