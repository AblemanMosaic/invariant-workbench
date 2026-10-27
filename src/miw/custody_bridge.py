"""Actual unchanged UCM manager/worker integration, fixture ceremony only.

No real Governor or production identity is established. The fixture demonstrator
runs trusted packaged code in a disposable directory, not arbitrary repositories.
"""
from __future__ import annotations
import base64
from pathlib import Path
import hashlib
import json
from .common import require,root,seal,write_json,BOUNDARY,read_bytes


def fixture_campaign(project_root:Path,out:Path)->dict:
    from uclop import project_intelligence as pi
    from uclop.custody import OpaqueEd25519KeyStore
    from uclop.protected_state import InMemoryMonotonicAnchor,ProtectedStateStore
    from uclop.workbench_orientation import build_fixture_orientation
    from uclop.workbench_manager import WorkbenchManager,create_plan
    from uclop.workbench_workers import BoundedWorker,snapshot_source
    require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS');out.mkdir(parents=True)
    source=out/'source';(source/'tests').mkdir(parents=True)
    code=read_bytes(project_root/'examples/assembly/operation.py')
    (source/'operation.py').write_bytes(code)
    (source/'contract.json').write_bytes(read_bytes(project_root/'examples/assembly/contract.json'))
    (source/'tests/__init__.py').write_bytes(b'')
    test=(b'import unittest\nfrom operation import assemble\n'
          b'class Inventory(unittest.TestCase):\n'
          b'    def test_last_kit(self): self.assertEqual(assemble(2,1,0,1),(True,0,0,1))\n'
          b'    def test_empty_stock(self): self.assertEqual(assemble(0,0,0,1),(False,0,0,0))\n'
          b'    def test_invalid_quantity(self): self.assertEqual(assemble(2,1,0,0),(False,2,1,0))\n')
    (source/'tests/test_inventory.py').write_bytes(test)
    snap=snapshot_source(source)
    records=[{'id':'REQ-INVENTORY','kind':'REQUIREMENT','title':'Inventory rule','summary':'Inspect the exact approved scalar rule','state':'OPEN','depends_on':[],'criterion':'Pinned source inspection'},
             {'id':'ART-ASSEMBLY','kind':'IMPLEMENTATION_ARTIFACT','title':'Assembly candidate','summary':'Prepare a bounded implementation-only change','state':'PLANNED','depends_on':['REQ-INVENTORY'],'path':'operation.py','sha256':None},
             {'id':'VER-CANDIDATE','kind':'VERIFICATION_OBLIGATION','title':'Candidate tests','summary':'Execute the exact trusted checking module against prepared candidate','state':'OPEN','depends_on':['ART-ASSEMBLY'],'evidence':[]}]
    records.sort(key=lambda r:r['id'])
    body={'schema':pi.SCHEMA,'project_id':'MIW-TURN3-FIXTURE','baseline':{'subject':'TRUSTED-PACKAGED-INVENTORY-FIXTURE','source_root':snap['source_root'],'review_disposition':'UNREVIEWED'},**BOUNDARY,'records':records}
    project={**body,'snapshot_root':pi.rooted(body)}
    fixture=build_fixture_orientation(roots={'project':project['snapshot_root'],'source':snap['source_root']})
    context=fixture['context'];pins={n:context[n] for n in ('project_root','source_root','registry_root','policy_root','charter_root','grant_root','jurisdiction_root')}
    # Exact candidate changes only a comment; semantics unchanged, bytes distinct.
    replacement=code+b'\n# Candidate prepared through the UCM bounded worker.\n'
    actions={'REQ-INVENTORY':{'operation':'INSPECT_ARTIFACTS','payload':{'paths':['contract.json','operation.py']}},
             'ART-ASSEMBLY':{'operation':'PREPARE_CANDIDATE','payload':{'changes':[{'path':'operation.py','original_sha256':hashlib.sha256(code).hexdigest(),'replacement_base64':base64.b64encode(replacement).decode()}]}},
             'VER-CANDIDATE':{'operation':'RUN_TESTS','payload':{'modules':['tests.test_inventory'],'candidate_task_id':'TASK-ART-ASSEMBLY'}}}
    plan=create_plan(project,pins=pins,task_actions=actions)
    keys=OpaqueEd25519KeyStore();state_key=keys.install_fixture_seed('WITNESS',b'S'*32);worker_key=keys.install_fixture_seed('NODE',b'W'*32)
    anchor=InMemoryMonotonicAnchor();store=ProtectedStateStore(out/'state',anchor=anchor,keys=keys,signing_handle=state_key)
    worker=BoundedWorker(source_directory=source,source_manifest=snap,output_directory=out/'outputs',bindings=pins,
                         tenant_id=context['tenant_id'],provider=keys,signing_handle=worker_key,expected_issuer=keys.identity(worker_key),
                         maximum_artifact_bytes=context['budgets']['max_artifact_bytes'],
                         trusted_tests={'tests.test_inventory':{'path':'tests/test_inventory.py','sha256':hashlib.sha256(test).hexdigest(),
                         'test_ids':['tests.test_inventory.Inventory.'+n for n in ('test_empty_stock','test_invalid_quantity','test_last_kit')]}})
    args={'project':project,'plan':plan,'orientation':context,'orientation_pins':fixture['external_pins'],
          'worker_identity':keys.identity(worker_key),'worker_root':worker.worker_root,'now':1000}
    manager=WorkbenchManager(store,expected_head={'sequence':0,'head':'GENESIS'},**args)
    start=manager.current_head
    for task,operation in [('REQ-INVENTORY','inspect'),('ART-ASSEMBLY','prepare'),('VER-CANDIDATE','test')]:
        result=manager.execute('TASK-'+task,operation,'miw-fixture',worker,expected_head=manager.current_head,now=1000)
    require(result['status']=='COMPLETE_INFORMATION_ONLY','UCM_FIXTURE_PLAN_INCOMPLETE')
    head=dict(result['current_head'])
    reopened=WorkbenchManager(store,expected_head=head,**args)
    require(reopened.status(expected_head=head,now=1000)['status']=='COMPLETE_INFORMATION_ONLY','UCM_FIXTURE_REOPEN_FAILED')
    stale_refused=False
    from uclop.canonical import Refusal
    try:WorkbenchManager(store,expected_head=start,**args)
    except Refusal:stale_refused=True
    require(stale_refused,'STALE_HEAD_NOT_REFUSED')
    canonical_unchanged=read_bytes(source/'operation.py')==code
    prepared=result['operations']['prepare']['result'];tested=result['operations']['test']['result']
    receipt_bound=root(prepared['receipt'])==tested['evidence']['result']['candidate_receipt_root']
    require(receipt_bound and canonical_unchanged,'UCM_CANDIDATE_BINDING')
    write_json(out/'PROJECT.json',project);write_json(out/'PLAN.json',plan);write_json(out/'STATUS.json',result)
    write_json(out/'PUBLIC-ORIENTATION.json',{'context':context,'external_pins':fixture['external_pins']})
    capsule=reopened.export_capsule(expected_head=head,now=1000);write_json(out/'CAPSULE.json',capsule)
    report=seal({'schema':'miw.ucm_manager_integration.v1',**BOUNDARY,'status':'PASSED_FIXTURE_CUSTODY_INTEGRATION',
                 'manager_status':result['status'],'project_obligations_satisfied':result['project_obligations_satisfied'],
                 'candidate_receipt_bound':receipt_bound,'canonical_source_unchanged':canonical_unchanged,'stale_external_head_refused':stale_refused,
                 'signature_algorithm':'Ed25519','identity_status':'PUBLISHED_FIXTURE_IDENTITIES_ONLY','production_signer':'NOT_BOUND',
                 'anchor':'PROCESS_LOCAL_FIXTURE_NOT_PRODUCTION_FRESHNESS','os_sandbox':'NOT_PROVIDED',
                 'executed_worker_operations':3,'trusted_candidate_tests':3,'final_head':head,'plan_root':plan['plan_root']})
    write_json(out/'SUMMARY.json',report);return report
