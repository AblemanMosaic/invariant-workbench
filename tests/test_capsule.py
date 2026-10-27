import unittest,tempfile,json,zipfile,hashlib,importlib.util,stat
from pathlib import Path
from helpers import ROOT
spec=importlib.util.spec_from_file_location('miw_capsule_verifier',ROOT/'VERIFY.py');verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)

class CapsuleTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.out=Path(self.tmp.name)/'candidate.zip'
    def archive(self,content=b'data',recorded=b'data',extra=None,mutate_manifest=None):
        m={'schema':'miw.capsule_manifest.v1','standing':'INFORMATION_ONLY','authority_effect':'NONE',
           'files':[{'path':'source.txt','bytes':len(recorded),'sha256':verifier.sha(recorded)}]}
        if mutate_manifest:mutate_manifest(m)
        m['manifest_root']=verifier.sha(verifier.canonical(m))
        with zipfile.ZipFile(self.out,'w') as z:
            z.writestr('source.txt',content);z.writestr('MANIFEST.json',verifier.canonical(m))
            if extra:z.writestr(extra,b'extra')
        return verifier.sha(self.out.read_bytes())
    def test_closed_world_archive_pass(self):
        pin=self.archive();r=verifier.verify(self.out,pin)
        self.assertEqual(r['status'],'PASS_BYTE_INTEGRITY_ONLY');self.assertEqual(r['candidate_imports'],0)
    def test_wrong_external_pin_refused(self):
        self.archive()
        with self.assertRaises(ValueError):verifier.verify(self.out,'0'*64)
    def test_altered_member_refused(self):
        pin=self.archive(content=b'changed')
        with self.assertRaises(ValueError):verifier.verify(self.out,pin)
    def test_extra_member_refused(self):
        pin=self.archive(extra='extra.txt')
        with self.assertRaises(ValueError):verifier.verify(self.out,pin)
    def test_path_traversal_refused(self):
        pin=self.archive(extra='../escape')
        with self.assertRaises(ValueError):verifier.verify(self.out,pin)
    def test_bytecode_refused(self):
        pin=self.archive(extra='bad.pyc')
        with self.assertRaises(ValueError):verifier.verify(self.out,pin)
    def test_case_collision_refused(self):
        pin=self.archive(extra='SOURCE.txt')
        with self.assertRaises(ValueError):verifier.verify(self.out,pin)
    def test_authority_promotion_refused(self):
        pin=self.archive(mutate_manifest=lambda m:m.update(authority_effect='PRODUCTION'))
        with self.assertRaises(ValueError):verifier.verify(self.out,pin)
