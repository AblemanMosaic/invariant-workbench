import unittest,tempfile,subprocess,sys,json
from pathlib import Path
from helpers import ROOT,example

class CLITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name)
    def call(self,*args):
        return subprocess.run([sys.executable,'-I','-B',str(ROOT/'tools/miw.py'),*map(str,args)],
                              capture_output=True,text=True,timeout=30)
    def test_help(self):
        r=self.call('--help');self.assertEqual(r.returncode,0);self.assertIn('verify-proof',r.stdout)
    def test_prove_and_replay(self):
        c=ROOT/'examples/assembly/contract.json';s=ROOT/'examples/assembly/operation.py';p=self.out/'proof.json'
        r=self.call('prove','--contract',c,'--source',s,'--out',p);self.assertEqual(r.returncode,0,r.stderr)
        r=self.call('verify-proof','--contract',c,'--source',s,'--proof',p);self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['outcome'],'CHECKED_SOURCE_PROOF')
    def test_unknown_is_nonzero_and_still_exported(self):
        c,s,_=example();src=self.out/'mutant.py';src.write_text(s.replace('a - 2*q','a'));p=self.out/'proof.json'
        r=self.call('prove','--contract',ROOT/'examples/assembly/contract.json','--source',src,'--out',p)
        self.assertEqual(r.returncode,3,r.stderr);self.assertEqual(json.loads(p.read_text())['outcome'],'UNKNOWN_PROOF')
    def test_unknown_inputs_fail_closed(self):
        r=self.call('import-zucchini','--report',self.out/'missing.json')
        self.assertEqual(r.returncode,2);self.assertEqual(json.loads(r.stderr)['status'],'REFUSED')
    def test_bad_json_does_not_traceback(self):
        p=self.out/'bad.json';p.write_text('{bad')
        r=self.call('import-zucchini','--report',p);self.assertEqual(r.returncode,2);self.assertNotIn('Traceback',r.stderr)
    def test_bdd_command(self):
        r=self.call('test-feature','--contract',ROOT/'examples/assembly/contract.json',
                    '--source',ROOT/'examples/assembly/operation.py','--feature',ROOT/'examples/assembly/inventory.feature')
        self.assertEqual(r.returncode,0,r.stderr)
    def test_import_command(self):
        r=self.call('import-zucchini','--report',ROOT/'fixtures/zucchini/rules.synthetic.json')
        self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['source_execution'],'NONE')
    def test_protected_existing_output_refused(self):
        p=self.out/'output.json';p.write_text('do not overwrite')
        r=self.call('import-zucchini','--report',ROOT/'fixtures/zucchini/rules.synthetic.json','--out',p)
        self.assertEqual(r.returncode,2);self.assertEqual(p.read_text(),'do not overwrite')
    def test_junit_binding_commands(self):
        a=ROOT/'fixtures/zucchini/rules.synthetic.json';b=ROOT/'fixtures/zucchini/results.synthetic.xml';p=self.out/'binding.json'
        r=self.call('bind-junit','--report',a,'--junit',b,'--out',p);self.assertEqual(r.returncode,0,r.stderr)
        r=self.call('link-junit','--report',a,'--junit',b,'--binding',p);self.assertEqual(r.returncode,0,r.stderr)
        self.assertEqual(json.loads(r.stdout)['proof_status'],'NOT_PROVED')
