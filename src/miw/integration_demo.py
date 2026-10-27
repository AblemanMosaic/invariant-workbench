"""One coherent local integration campaign. External missing legs stay NOT_RUN."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import time
import shutil
from .common import read_json,read_bytes,write_json,seal,root,digest,require,Refusal,BOUNDARY,canonical_bytes
from .lifecycle import lifecycle_demo,bounded_exploration
from .proposals import proposal_request,review_proposal
from .changes import explain_change
from .governance import freeze_basis,check_candidate
from .proofs import prove_source,verify_source_proof
from .bdd import discover,run_feature
from .external_build import preflight

def maintenance_case(project:Path,out:Path)->dict:
    require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS');out.mkdir(parents=True)
    old=read_json(project/'examples/assembly/contract.json')
    old_source=read_bytes(project/'examples/assembly/operation.py').decode()
    old_feature=read_bytes(project/'examples/assembly/inventory.feature').decode()
    new=deepcopy(old);new['title']='Consume three A and one B per finished unit, or refuse unchanged'
    new['accept_when']=new['accept_when'].replace('2*q','3*q')
    new['accepted']['a']=new['accepted']['a'].replace('2*q','3*q')
    for inv in new['invariants']:
        if inv['id']=='REQ_A_CONSERVATION':inv['formula']=inv['formula'].replace('2*','3*')
    new['witnesses'][0]['inputs']['a']=3
    source=old_source.replace('2*q','3*q')
    feature=old_feature.replace('inputs a=2, b=1','inputs a=3, b=1').replace('And a is 3\n  And b is 2','And a is 0\n  And b is 2')
    for name,value in [('before.contract.json',old),('after.contract.json',new),('CHANGE.json',explain_change(old,new,old_source,source))]:write_json(out/name,value)
    for name,value in [('before.py',old_source),('after.py',source),('before.feature',old_feature),('after.feature',feature)]: (out/name).write_text(value,encoding='utf-8')
    t=time.perf_counter();prior=prove_source(old,old_source);prior_check=verify_source_proof(old,old_source,prior);before_ms=int((time.perf_counter()-t)*1000)
    write_json(out/'before.proof.json',prior);write_json(out/'before.check.json',prior_check)
    refused=False;code=None
    try:verify_source_proof(new,source,prior)
    except Refusal as exc:refused=True;code=exc.code
    require(refused,'OLD_PROOF_SILENTLY_REUSED')
    obsolete=discover(new,old_feature);require(not obsolete['discovery_success'],'OLD_EXAMPLES_NOT_INVALIDATED')
    write_json(out/'old_examples_new_contract.json',obsolete)
    t=time.perf_counter();proof=prove_source(new,source);checked=verify_source_proof(new,source,proof);after_ms=int((time.perf_counter()-t)*1000)
    require(checked['outcome']=='CHECKED_SOURCE_PROOF' and checked['residual_count']==0,'MAINTENANCE_REQUALIFICATION_FAILED')
    write_json(out/'after.proof.json',proof);write_json(out/'after.check.json',checked)
    tested=run_feature(new,source,feature);require(all(r['status']=='PASSED' for r in tested['runs']),'MAINTENANCE_EXAMPLES_FAILED')
    write_json(out/'after.execution.json',tested)
    summary=seal({'schema':'miw.maintenance_exercise.v1',**BOUNDARY,'status':'PASSED_SCALAR_REQUALIFICATION_EXERCISE',
                  'change':'Recipe A coefficient 2 -> 3','old_proof_reuse_refused':refused,'refusal_code':code,
                  'old_scenarios_inconsistent':not obsolete['discovery_success'],'after_check':checked,
                  'after_examples_passed':len(tested['runs']),
                  'changed_contract_fields':[k for k in sorted(old) if old[k]!=new[k]],
                  'machine_observation_ms':{'prove_and_replay_before':before_ms,'prove_and_replay_after':after_ms},
                  'human_maintenance_effort':'NOT_MEASURED; BUILDER_SCRIPTED_CHANGE',
                  'economic_improvement_claim':False,'production_specification_approval':'NOT_GRANTED',
                  'existing_order_behavior':'SEPARATELY_TESTED_LIFECYCLE_PRESERVES_ORIGINAL_RECIPE_VERSION'})
    write_json(out/'SUMMARY.json',summary);return summary

def proposals_case(project:Path,out:Path)->dict:
    require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS');out.mkdir(parents=True)
    baseline=out/'checking_basis';baseline.mkdir()
    c=read_json(project/'examples/assembly/contract.json');s=read_bytes(project/'examples/assembly/operation.py').decode()
    defective=s.replace('a - 2*q','a')
    require(defective!=s,'FIXTURE_MUTATION_MISSING')
    (baseline/'operation.py').write_text(defective,encoding='utf-8');write_json(baseline/'contract.json',c)
    (baseline/'inventory.feature').write_bytes(read_bytes(project/'examples/assembly/inventory.feature'))
    for name in ('contracts.py','bdd.py','restricted.py','proofs.py'):
        (baseline/name).write_bytes(read_bytes(project/'src/miw'/name))
    protected={'SPECIFICATION':['contract.json','inventory.feature'],'ORACLE':['contracts.py'],
               'DRIVER':['restricted.py'],'RUNNER':['bdd.py'],'CHECKER':['proofs.py']}
    basis=freeze_basis(baseline,protected,['operation.py']);write_json(out/'BASIS.json',basis)
    req=proposal_request(c,defective,c['state_requirements']['a'],basis['basis_root'],budget=8)
    response={'kind':'SCENARIO_PROPOSAL','request_root':req['request_root'],'feature':read_bytes(baseline/'inventory.feature').decode()}
    reviewed=review_proposal(req,canonical_bytes(response),expected_request_root=req['request_root'],current_contract=c,current_source=defective,current_basis_root=basis['basis_root'])
    require(reviewed['assessment']['outcome']=='REPRODUCED_REQUIREMENT_FAILURE','PROPOSAL_TARGET_NOT_REPRODUCED')
    candidate=out/'implementation_candidate';shutil.copytree(baseline,candidate);(candidate/'operation.py').write_text(s,encoding='utf-8')
    scope=check_candidate(basis,candidate,basis['basis_root'])
    # Try a checking-basis edit in a different disposable tree, never canonical.
    attacked=out/'rejected_candidate';shutil.copytree(candidate,attacked);(attacked/'bdd.py').write_text('# removed checking machinery\n')
    protected_refusal=None
    try:check_candidate(basis,attacked,basis['basis_root'])
    except Refusal as exc:protected_refusal=exc.code
    require(protected_refusal=='VERIFICATION_BASIS_CHANGED','CHECKING_BASIS_CHANGE_NOT_REFUSED')
    for name,v in [('REQUEST.json',req),('RESPONSE.json',response),('REVIEW.json',reviewed),('SCOPE.json',scope)]:write_json(out/name,v)
    summary=seal({'schema':'miw.proposal_campaign.v1',**BOUNDARY,'status':'PASSED_OFFLINE_PROPOSAL_REVIEW',
                  'model_execution':'NOT_RUN','proposal_origin':'BUILDER_AUTHORED_FIXTURE_NOT_AI_OUTPUT',
                  'target':req['target'],'target_failure':reviewed['assessment']['outcome'],
                  'implementation_edit':scope['status'],'checker_edit':protected_refusal,
                  'specification_approval':'NOT_GRANTED','os_sandbox':'NOT_PROVIDED',
                  'basis_root':basis['basis_root'],'request_root':req['request_root']})
    write_json(out/'SUMMARY.json',summary);return summary

def generate_integration(project:Path,out:Path)->dict:
    require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS');out.mkdir(parents=True)
    lifecycle=lifecycle_demo();exploration=bounded_exploration()
    write_json(out/'lifecycle/SUMMARY.json',lifecycle);write_json(out/'lifecycle/FINITE-EXPLORATION.json',exploration)
    proposals=proposals_case(project,out/'proposals');maintenance=maintenance_case(project,out/'maintenance')
    from .custody_bridge import fixture_campaign
    custody=fixture_campaign(project,out/'custody')
    from .foundry_view import headless_smoke
    ui=headless_smoke();write_json(out/'ui/HEADLESS.json',ui)
    observed=preflight();write_json(out/'PREFLIGHT.json',observed)
    summary=seal({'schema':'miw.turn3_integration_summary.v1',**BOUNDARY,'status':'BUILDER_CHECKED_WITH_OPEN_EXTERNAL_GATES',
                 'lifecycle':'TESTED_REFERENCE_MODEL','finite_graph':{'states':exploration['states'],'edges':exploration['edges'],'unbounded_proof':False},
                 'proposals':proposals['status'],'maintenance':maintenance['status'],'ucm_manager':custody['status'],
                 'mosaic_ui':'ACTUAL_FOUNDRY_HEADLESS_AND_WIN32_BINDING','native_windows':'NOT_RUN_BY_INTEGRATION_DEMO',
                 'zucchini_live':'NOT_RUN_BY_INTEGRATION_DEMO','postgres_live':'NOT_RUN_BY_INTEGRATION_DEMO','local_ai_model':'NOT_RUN_BY_INTEGRATION_DEMO',
                 'production_custody':'NOT_BOUND','independent_review':'NOT_PERFORMED',
                 'record_roots':{'lifecycle':lifecycle['record_root'],'exploration':exploration['record_root'],
                                 'proposals':proposals['record_root'],'maintenance':maintenance['record_root'],
                                 'custody':custody['record_root'],'headless':ui['record_root']},
                 'limits':['no C++ formal proof','no live transaction/concurrency qualification',
                           'no independent compiler correspondence theorem','no full inherited UCM review closure',
                           'no measured human cost advantage']})
    write_json(out/'SUMMARY.json',summary);return summary
