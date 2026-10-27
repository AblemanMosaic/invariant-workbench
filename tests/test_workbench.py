import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from miw.common import Refusal, read_json
from miw.workbench import (
    build_workspace, compare_workspaces, execute_local, explain_obligation,
    lower_obligation, propose_binding, select_obligation,
)


class InvariantWorkbenchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dossier=ROOT/'evidence/invariant-workbench-demo-v8'

    def test_workspace_preserves_evidence_classes_and_unbound_zucchini(self):
        workspace=build_workspace(self.dossier)
        self.assertEqual(len(workspace['obligations']),9)
        row=next(x for x in workspace['obligations'] if x['id']=='REQ_ACCEPTANCE')
        self.assertIn('SUBJECT_PROOF',row['evidence_classes'])
        self.assertEqual(row['zucchini_projection'],'UNBOUND')
        self.assertIn('NoAssemblyWithoutStock',workspace['unbound_zucchini_requirements'])

    def test_explicit_proposed_binding_does_not_promote_to_proof(self):
        bindings=read_json(ROOT/'examples/assembly/workbench.bindings.json')
        workspace=build_workspace(self.dossier,bindings)
        row=next(x for x in workspace['obligations'] if x['id']=='REQ_ACCEPTANCE')
        self.assertEqual(row['zucchini_projection'],'BOUND')
        zucchini=next(x for x in row['evidence'] if x['class']=='ZUCCHINI_DECLARATION')
        self.assertEqual(zucchini['status'],'BOUND_PROPOSED')
        self.assertEqual(row['proof_projection'],'FORMALLY_CHECKED_IN_SUBJECT')

    def test_binding_selection_lowering_explanation_and_comparison(self):
        workspace=build_workspace(self.dossier)
        proposal=propose_binding(workspace,'REQ_ACCEPTANCE','NoAssemblyWithoutStock','CANDIDATE_CORRESPONDENCE','Review meanings before adoption.')
        self.assertEqual(proposal['standing'],'PROPOSED')
        selected=select_obligation(workspace,'REQ_ACCEPTANCE','PROOF_RECHECK')
        lowering=lower_obligation(workspace,selected,'PROOF_RECHECK')
        self.assertEqual(lowering['result'],'BOUNDED')
        explanation=explain_obligation(workspace,'REQ_ACCEPTANCE')
        self.assertIn('requirement',explanation)
        self.assertTrue(compare_workspaces(workspace,workspace)['same'])

    def test_unbound_zucchini_lowering_refuses(self):
        workspace=build_workspace(self.dossier)
        selected=select_obligation(workspace,'REQ_ACCEPTANCE','ZUCCHINI_REVIEW')
        lowering=lower_obligation(workspace,selected,'ZUCCHINI_REVIEW')
        self.assertEqual(lowering['result'],'REFUSED')
        self.assertEqual(lowering['refusal_code'],'WORKBENCH_REQUIRED_EVIDENCE_ABSENT')

    def test_local_execution_requires_opt_in_and_rechecks_exact_subject(self):
        workspace=build_workspace(self.dossier)
        selected=select_obligation(workspace,'REQ_ACCEPTANCE','PROOF_RECHECK')
        lowering=lower_obligation(workspace,selected,'PROOF_RECHECK')
        with self.assertRaisesRegex(Refusal,'WORKBENCH_LOCAL_EXECUTION_NOT_AUTHORIZED'):
            execute_local(lowering,self.dossier)
        receipt=execute_local(lowering,self.dossier,allow_local_check=True)
        self.assertEqual(receipt['outcome'],'CHECKED_SOURCE_PROOF')

    def test_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);workspace=out/'workspace.json';selection=out/'selection.json';lowering=out/'lowering.json';receipt=out/'receipt.json'
            def call(*args):
                return subprocess.run([sys.executable,'-I','-B',str(ROOT/'tools/miw.py'),*map(str,args)],capture_output=True,text=True,timeout=60)
            result=call('workbench-open','--directory',self.dossier,'--bindings',ROOT/'examples/assembly/workbench.bindings.json','--out',workspace);self.assertEqual(result.returncode,0,result.stderr)
            result=call('workbench-select','--workspace',workspace,'--requirement','REQ_ACCEPTANCE','--lane','PROOF_RECHECK','--out',selection);self.assertEqual(result.returncode,0,result.stderr)
            result=call('workbench-lower','--workspace',workspace,'--selection',selection,'--target','PROOF_RECHECK','--out',lowering);self.assertEqual(result.returncode,0,result.stderr)
            result=call('workbench-run','--lowering',lowering,'--directory',self.dossier,'--workspace',workspace,'--allow-local-check','--out',receipt);self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(receipt.read_text())['outcome'],'CHECKED_SOURCE_PROOF')

    def test_mosaic_controller_selects_lowers_runs_and_proposes(self):
        from miw.foundry_view import make_headless
        ui=make_headless(self.dossier);controller=ui.miw_controller
        controller.dispatch({'intent':'ACTIVATE','node_id':'nav_workbench'})
        controller.dispatch({'intent':'ACTIVATE','node_id':'workbench_validate'})
        self.assertEqual(ui.state['status'],'WORKSPACE VALIDATED')
        controller.dispatch({'intent':'TEXT_COMMIT','node_id':'workbench_lane','value':'PROOF_RECHECK'})
        controller.dispatch({'intent':'ACTIVATE','node_id':'workbench_lower'})
        self.assertEqual(ui.state['status'],'LOWERED BOUNDED')
        controller.dispatch({'intent':'ACTIVATE','node_id':'workbench_run'})
        self.assertEqual(ui.state['status'],'LOCAL CHECK CHECKED_SOURCE_PROOF')
        controller.dispatch({'intent':'ACTIVATE','node_id':'workbench_bind'})
        self.assertEqual(ui.state['status'],'BINDING PROPOSED | NOT ADOPTED')

