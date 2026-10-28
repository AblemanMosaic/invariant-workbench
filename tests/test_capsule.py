import unittest,tempfile,json,zipfile,hashlib,importlib.util,stat
from pathlib import Path
from helpers import ROOT
spec=importlib.util.spec_from_file_location('miw_capsule_verifier',ROOT/'VERIFY.py');verifier=importlib.util.module_from_spec(spec);spec.loader.exec_module(verifier)
seal_spec=importlib.util.spec_from_file_location('miw_capsule_sealer',ROOT/'tools'/'seal.py');sealer=importlib.util.module_from_spec(seal_spec);seal_spec.loader.exec_module(sealer)

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

    def test_sealer_excludes_only_root_git_metadata(self):
        root=Path(self.tmp.name)/'source';root.mkdir();(root/'kept.txt').write_text('kept')
        (root/'.git').mkdir();(root/'.git'/'config').write_text('local-only')
        (root/'nested').mkdir();(root/'nested'/'.git-note').write_text('kept')
        names=[path.relative_to(root).as_posix() for path in sealer.source_files(root)]
        self.assertEqual(names,['kept.txt','nested/.git-note'])

    def directory(self):
        root=Path(self.tmp.name)/'checkout';root.mkdir();data=b'data\n'
        (root/'source.txt').write_bytes(data)
        m={'schema':'miw.capsule_manifest.v1','standing':'INFORMATION_ONLY','authority_effect':'NONE',
           'files':[{'path':'source.txt','bytes':len(data),'sha256':verifier.sha(data)}]}
        m['manifest_root']=verifier.sha(verifier.canonical(m))
        (root/'MANIFEST.json').write_bytes(verifier.canonical(m))
        return root

    def test_closed_world_directory_pass_and_git_metadata_is_ignored(self):
        root=self.directory();(root/'.git').mkdir();(root/'.git'/'config').write_text('local-only')
        result=verifier.verify_directory(root)
        self.assertEqual(result['status'],'PASS_DIRECTORY_BYTE_INTEGRITY_ONLY')
        self.assertEqual(result['ignored_paths'],['.git/'])

    def test_directory_extra_member_refused(self):
        root=self.directory();(root/'extra.txt').write_text('extra')
        with self.assertRaisesRegex(ValueError,'CLOSED_WORLD_MEMBER_MISMATCH'):
            verifier.verify_directory(root)

    def test_directory_changed_member_refused(self):
        root=self.directory();(root/'source.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'MEMBER_DIGEST_MISMATCH'):
            verifier.verify_directory(root)
