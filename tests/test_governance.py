import unittest,tempfile,shutil,os
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from miw.common import Refusal,safe_relative
from miw.governance import freeze_basis,check_candidate,snapshot,ROLES
from miw.graph import make_graph,impact
from helpers import reseal,directory_alias

class GovernanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)/'base';self.base.mkdir();self.candidate=Path(self.temp.name)/'candidate'
        self.protected={role:[role.lower()+'.txt'] for role in ROLES}
        for paths in self.protected.values():(self.base/paths[0]).write_text('fixed basis')
        (self.base/'operation.py').write_text('original implementation')
        (self.base/'other.txt').write_text('not editable')
        self.basis=freeze_basis(self.base,self.protected,['operation.py'])
        shutil.copytree(self.base,self.candidate)
    def check(self):return check_candidate(self.basis,self.candidate,self.basis['basis_root'])
    def test_exact_mutable_change_permitted_but_not_correctness(self):
        (self.candidate/'operation.py').write_text('candidate implementation')
        r=self.check();self.assertEqual(r['status'],'WITHIN_DECLARED_EDIT_SCOPE')
        self.assertEqual(r['correctness_status'],'NOT_ESTABLISHED');self.assertEqual(r['authority_effect'],'NONE')
    def test_no_change_valid(self):self.assertEqual(self.check()['changed_paths'],[])
    def test_external_pin_required(self):
        with self.assertRaises(Refusal):check_candidate(self.basis,self.candidate,'0'*64)
    def test_new_file_refused(self):
        (self.candidate/'new.txt').write_text('new')
        with self.assertRaises(Refusal):self.check()
    def test_deleted_file_refused(self):
        (self.candidate/'operation.py').unlink()
        with self.assertRaises(Refusal):self.check()
    def test_out_of_scope_change_refused(self):
        (self.candidate/'other.txt').write_text('changed')
        with self.assertRaises(Refusal):self.check()
    def test_missing_role_refused(self):
        p=deepcopy(self.protected);p.pop('ORACLE')
        with self.assertRaises(Refusal):freeze_basis(self.base,p,['operation.py'])
    def test_mutable_basis_overlap_refused(self):
        with self.assertRaises(Refusal):freeze_basis(self.base,self.protected,['oracle.txt'])
    def test_symlink_refused(self):
        p=self.candidate/'operation.py';p.unlink()
        if os.name=='nt':directory_alias(p,self.base)
        else:p.symlink_to(self.base/'operation.py')
        with self.assertRaises(Refusal):self.check()
    def test_hardlink_refused(self):
        p=self.candidate/'operation.py';p.unlink()
        try:os.link(self.base/'operation.py',p)
        except OSError:self.skipTest('Host does not permit hardlink fixture')
        with self.assertRaises(Refusal):self.check()
    def test_case_collision_refused(self):
        if os.name!='nt':(self.candidate/'OTHER.txt').write_text('collision')
        walked=[(str(self.candidate),[],['other.txt','OTHER.txt'])]
        with patch('miw.governance.os.walk',return_value=walked):
            with self.assertRaises(Refusal):snapshot(self.candidate)
    def test_resealed_basis_does_not_match_external_pin(self):
        b=deepcopy(self.basis);b['mutable_paths'].append('oracle.txt');reseal(b,'basis_root')
        with self.assertRaises(Refusal):check_candidate(b,self.candidate,self.basis['basis_root'])
    def test_read_only_checker_does_not_mutate_base_or_candidate(self):
        before=snapshot(self.base),snapshot(self.candidate);self.check()
        self.assertEqual(before,(snapshot(self.base),snapshot(self.candidate)))

for role in sorted(ROLES):
    def case(self,role=role):
        (self.candidate/self.protected[role][0]).write_text('weakened checking basis')
        with self.assertRaises(Refusal):self.check()
    setattr(GovernanceTests,'test_protect_'+role.lower(),case)
for i,path in enumerate(['../x','/tmp/x','C:/x','a\\b','a//b','a/./b','a/../b','a.','a ','']):
    def case(self,path=path):
        with self.assertRaises(Refusal):safe_relative(path)
    setattr(GovernanceTests,'test_unsafe_path_'+str(i),case)

class GraphTests(unittest.TestCase):
    def setUp(self):
        self.nodes=[{'id':x,'kind':'ARTIFACT','root':x} for x in ('spec','source','proof','integration')]
        self.edges=[{'dependency':'spec','dependent':'proof','relation':'CHECKS'},
                    {'dependency':'source','dependent':'proof','relation':'CHECKS'}]
        self.g=make_graph(self.nodes,self.edges,'Selected demo scope')
    def test_partial_graph_never_narrows_qualification(self):
        r=impact(self.g,['source'],self.g['graph_root'])
        self.assertEqual(r['known_dependency_closure'],['proof','source'])
        self.assertEqual(r['required_requalification'],['integration','proof','source','spec'])
    def test_unknown_change_forces_full_scope(self):
        r=impact(self.g,['external_db'],self.g['graph_root'])
        self.assertEqual(r['mode'],'FULL_REQUALIFICATION');self.assertEqual(r['unknown_changes'],['external_db'])
    def test_forged_complete_graph_refused(self):
        g=deepcopy(self.g);g['complete']=True;reseal(g,'graph_root')
        with self.assertRaises(Refusal):impact(g,['source'],g['graph_root'])
    def test_bad_edge_refused(self):
        with self.assertRaises(Refusal):make_graph(self.nodes,[{'dependency':'unknown','dependent':'proof','relation':'CHECKS'}],'scope')
    def test_wrong_external_pin_refused(self):
        with self.assertRaises(Refusal):impact(self.g,['source'],'0'*64)
