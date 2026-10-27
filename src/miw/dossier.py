"""Reproducible demonstration and offline evidence dossier."""
from __future__ import annotations
from pathlib import Path
from copy import deepcopy
from html import escape
import json
import tempfile
import shutil
from .common import BOUNDARY,require,seal,check_seal,read_bytes,read_json,write_json,digest,root,safe_relative,exact_keys,canonical_bytes
from .proofs import prove_source,verify_source_proof
from .bdd import run_feature,assess_counterexample,assessment_from_execution,validate_execution_record,validate_assessment_record
from .zucchini import import_report,make_junit_binding,link_junit
from .graph import make_graph,impact
from .governance import freeze_basis,check_candidate,ROLES

MUTANTS=[
 ('NO_A_CONSUMPTION','a - 2*q','a','REQ_A_ACCOUNTING'),
 ('WRONG_B_CONSUMPTION','b - q','b - 2*q','REQ_B_ACCOUNTING'),
 ('OUTPUT_NOT_RECORDED','f + q','f','REQ_FINISHED_ACCOUNTING'),
 ('ZERO_ACCEPTED','q <= 0','q < 0','REQ_ACCEPTANCE'),
 ('LAST_KIT_REFUSED','a < 2*q','a <= 2*q','REQ_ACCEPTANCE'),
 ('REFUSAL_MUTATES','return (False, a, b, f)','return (False, a, b, f + 1)','REQ_FINISHED_ACCOUNTING'),
]

def render_summary(summary:dict) -> str:
    def esc(x):return escape(str(x),quote=True)
    proof_rows=''.join('<tr><td>'+esc(e['name'])+'</td><td>'+esc(e['proof_outcome'])+'</td><td>'+str(e['path_count'])+
        '</td><td>'+str(e['native_vc_count'])+'</td><td>'+str(e['scenario_passes'])+' / '+str(e['scenario_count'])+'</td></tr>'
        for e in summary['examples'])
    mutant_rows=''.join('<tr><td>'+esc(m['id'])+'</td><td>'+esc(m['proof_outcome'])+'</td><td>'+esc(m['counterexample_outcome'])+
                        '</td><td>'+esc(m['target'])+'</td></tr>' for m in summary['mutations'])
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; base-uri 'none'; form-action 'none'">
<title>Mosaic Invariant Workbench | Turn 4 scalar evidence</title>
<style>body{background:#11161d;color:#edf1f6;font:16px/1.6 system-ui,sans-serif;margin:0}main{max-width:1120px;margin:auto;padding:40px 30px}h1{font-size:36px;line-height:1.15}h2{margin-top:36px}small,.muted{color:#b2becd}.boundary{border-left:4px solid #d7b97c;padding:12px 20px;background:#202631}.cards{display:flex;gap:16px;flex-wrap:wrap}.card{flex:1;min-width:180px;border:1px solid #384250;border-radius:8px;padding:18px}.big{font-size:30px;font-weight:700}table{width:100%;border-collapse:collapse;font-size:14px}td,th{border-bottom:1px solid #39424d;text-align:left;padding:12px 8px}code,pre{font-family:monospace;overflow-wrap:anywhere}pre{white-space:pre-wrap;background:#1b222c;padding:16px;border-radius:8px}a{color:#a8d7ff}details{margin:20px 0}summary{cursor:pointer}.scroll{overflow:auto}</style></head><body><main>
<p class="muted">MOSAIC / INVARIANT WORKBENCH / TURN 4 CANDIDATE</p>
<h1>Rules. Code. Evidence.</h1>
<p>A local demonstration of pre-execution source verification, requirement-linked examples, and bounded Zucchini interoperability.</p>
<div class="boundary"><strong>Information only. No release or production authority.</strong><br>
The proof concerns a closed, loop-free Python subset. The new source translator is trusted, not formally proved. C++, database concurrency, and physical stock are outside the claim.</div>
<h2>Checked source, before execution</h2><div class="scroll"><table><thead><tr><th>Operation</th><th>Result</th><th>Path clauses</th><th>Native VCs</th><th>Example tests</th></tr></thead><tbody>'''+proof_rows+'''</tbody></table></div>
<p class="muted">Proofs quantify over valid mathematical integer inputs under the stated trusted semantics. The example counts are separate observations, not the proof.</p>
<h2>Deliberately defective implementations</h2><div class="scroll"><table><thead><tr><th>Mutation</th><th>Proof result</th><th>Executed counterexample</th><th>Named requirement</th></tr></thead><tbody>'''+mutant_rows+'''</tbody></table></div>
<p>UNKNOWN_PROOF is not itself a counterexample. The third column records a separate, requirement-specific executed failure.</p>
<h2>Zucchini adapter</h2><p>The included report and JUnit inputs are <strong>synthetic contract fixtures</strong>, not output from an upstream C++ build. Discovery coverage, execution status, proof, and failure attribution remain separate. A caller binding identifies the chosen files; it does not authenticate their origin.</p>
<h2>Protected checking basis</h2><p>The local edit-scope demonstration permits a change to the operation while refusing changes to the specification, oracle, driver, runner, and checker. It is not an OS sandbox or a signed UCM work-manager grant.</p>
<h2>Dependency map</h2><p>The map is deliberately partial. Known impact is shown, but all declared nodes require requalification. No dependency completeness claim is inferred.</p>
<details><summary>Exact demonstration summary</summary><pre>'''+esc(json.dumps(summary,indent=2,sort_keys=True))+'''</pre></details>
<p><a href="SUMMARY.json">Machine-readable summary</a> · <a href="DEMO-MANIFEST.json">Dossier file inventory</a></p>
<p class="muted">No JavaScript, external assets, network services, telemetry, or hosted model is required.</p>
</main></body></html>'''

def generate_demo(project:Path,out:Path) -> dict:
    require(not out.exists(),'OUTPUT_DIRECTORY_ALREADY_EXISTS',detail=str(out));out.mkdir(parents=True)
    examples=[];phases=[]
    for name in ['assembly','allocation']:
        base=project/'examples'/name
        c=read_json(base/'contract.json');s=read_bytes(base/'operation.py').decode('utf-8')
        feature=read_bytes(next(base.glob('*.feature'))).decode('utf-8')
        p=prove_source(c,s);phases.append({'phase':'STATIC_PROOF_BUILT','example':name,'source_execution':'NONE','proof_root':p['proof_root']})
        v=verify_source_proof(c,s,p);phases.append({'phase':'STATIC_PROOF_RECHECKED','example':name,'source_execution':'NONE','check_root':v['check_root']})
        require(v['outcome']=='CHECKED_SOURCE_PROOF','DEMO_PROOF_NOT_ESTABLISHED')
        run=run_feature(c,s,feature);phases.append({'phase':'EXAMPLES_EXECUTED','example':name,'execution_root':run['execution_root']})
        prefix=name+'.'
        write_json(out/(prefix+'contract.json'),c)
        (out/(prefix+'source.py')).write_text(s,encoding='utf-8',newline='\n')
        (out/(prefix+'feature')).write_text(feature,encoding='utf-8',newline='\n')
        write_json(out/(prefix+'proof.json'),p);write_json(out/(prefix+'proof-check.json'),v)
        write_json(out/(prefix+'execution.json'),run)
        examples.append({'name':name,'proof_outcome':v['outcome'],'proof_root':p['proof_root'],'subject_root':v['subject_root'],
            'path_count':v['path_count'],'obligation_count':v['obligation_count'],'native_vc_count':v['native_vc_count'],
            'scenario_count':len(run['runs']),'scenario_passes':sum(x['status']=='PASSED' for x in run['runs']),
            'residual_count':v['residual_count']})
    c=read_json(project/'examples/assembly/contract.json');s=read_bytes(project/'examples/assembly/operation.py').decode()
    feature=read_bytes(project/'examples/assembly/inventory.feature').decode()
    mutations=[]
    variants=[(name,s.replace(old,new),target) for name,old,new,target in MUTANTS]
    variants.append(('ALWAYS_REFUSE','def assemble(a, b, f, q):\n    return (False, a, b, f)\n','REQ_ACCEPTANCE'))
    for name,mutated,target in variants:
        proof=prove_source(c,mutated);verify_source_proof(c,mutated,proof)
        execution=run_feature(c,mutated,feature)
        counterexample=assessment_from_execution(c,mutated,feature,target,execution)
        require(proof['outcome']=='UNKNOWN_PROOF','MUTATION_UNEXPECTED_PROOF')
        require(counterexample['outcome']=='REPRODUCED_REQUIREMENT_FAILURE','MUTATION_NO_REPRODUCED_FAILURE')
        write_json(out/f'mutant.{name}.proof.json',proof)
        write_json(out/f'mutant.{name}.counterexample.json',counterexample)
        write_json(out/f'mutant.{name}.execution.json',execution)
        (out/f'mutant.{name}.source.py').write_text(mutated,encoding='utf-8',newline='\n')
        mutations.append({'id':name,'target':target,'proof_outcome':proof['outcome'],
            'counterexample_outcome':counterexample['outcome'],'failed_assertions':len(counterexample['failures']),
            'residual_count':len(proof['conservation']['residual_inventory']['obligations'])})
    report_raw=read_bytes(project/'fixtures/zucchini/rules.synthetic.json')
    junit_raw=read_bytes(project/'fixtures/zucchini/results.synthetic.xml')
    imported=import_report(report_raw);binding=make_junit_binding(report_raw,junit_raw)
    linked=link_junit(report_raw,junit_raw,binding)
    (out/'zucchini.report.json').write_bytes(report_raw)
    (out/'zucchini.junit.xml').write_bytes(junit_raw)
    write_json(out/'zucchini.import.json',imported);write_json(out/'zucchini.binding.json',binding)
    write_json(out/'zucchini.execution-link.json',linked)
    with tempfile.TemporaryDirectory(prefix='miw-scope-') as tmp:
        base=Path(tmp)/'baseline';base.mkdir();candidate=Path(tmp)/'candidate'
        protected={role:[role.lower()+'.txt'] for role in ROLES}
        for role,files in protected.items():(base/files[0]).write_bytes(('Frozen '+role).encode('utf-8'))
        (base/'operation.py').write_bytes(s.encode('utf-8'))
        basis=freeze_basis(base,protected,['operation.py']);shutil.copytree(base,candidate)
        (candidate/'operation.py').write_bytes((s+'\n').encode('utf-8'))
        allowed=check_candidate(basis,candidate,basis['basis_root'])
        from .common import Refusal
        refusals=[]
        for role in sorted(ROLES):
            path=candidate/protected[role][0];original=path.read_bytes();path.write_bytes(b'changed')
            try:check_candidate(basis,candidate,basis['basis_root'])
            except Refusal as exc:refusals.append({'role':role,'code':exc.code})
            else:raise Refusal('PROTECTED_BASIS_MUTATION_ACCEPTED')
            path.write_bytes(original)
        gov=seal({'schema':'miw.scope_demo.v1',**BOUNDARY,'basis':basis,'allowed_candidate':allowed,'protected_mutation_refusals':refusals,
                  'authorization':'FIXTURE_POLICY_ONLY_NO_SIGNER_OR_PRODUCTION_GRANT'},'demo_root')
    write_json(out/'governance.demo.json',gov)
    nodes=[{'id':'contract','kind':'REQUIREMENT','root':root(c)},
           {'id':'source','kind':'IMPLEMENTATION','root':digest(s.encode())},
           {'id':'proof','kind':'CHECKED_PROOF','root':examples[0]['proof_root']},
           {'id':'scenarios','kind':'SCENARIO_SPECIFICATION','root':digest(feature.encode())},
           {'id':'execution','kind':'EXECUTED_EXAMPLES','root':read_json(out/'assembly.execution.json')['execution_root']},
           {'id':'zucchini','kind':'IMPORTED_DECLARATIONS','root':imported['import_root']},
           {'id':'database_boundary','kind':'OPEN_OBLIGATION','root':'UNBOUND'},
           {'id':'physical_inventory','kind':'EMPIRICAL_ASSUMPTION','root':'UNVERIFIED'}]
    edges=[{'dependency':a,'dependent':b,'relation':r} for a,b,r in
           [('contract','proof','CHECKS'),('source','proof','CHECKS'),('contract','scenarios','CHECKS'),
            ('scenarios','execution','OBSERVES'),('source','execution','OBSERVES'),('source','database_boundary','DEPENDS_ON')]]
    graph=make_graph(nodes,edges,'Inventory demonstrator plus named unresolved external boundaries')
    impact_record=impact(graph,['source'],graph['graph_root'])
    write_json(out/'graph.json',graph);write_json(out/'impact.json',impact_record)
    summary=seal({'schema':'miw.turn4_scalar_demo.v1',**BOUNDARY,'turn':4,'examples':examples,'mutations':mutations,'phases':phases,
        'zucchini_validation':'THIS_DOSSIER_SYNTHETIC_FIXTURES_ONLY','zucchini_live_cpp':'NOT_RUN_BY_DOSSIER_GENERATOR',
        'scope_check_protected_roles':len(refusals),'graph_completeness':'PARTIAL_FULL_REQUALIFICATION_REQUIRED',
        'database':'SEPARATE_REFERENCE_ADAPTER_LIVE_NOT_RUN','physical_inventory':'NOT_VERIFIED','independent_review':'NOT_PERFORMED',
        'runtime_inputs':'No production data; synthetic examples only'},'summary_root')
    write_json(out/'SUMMARY.json',summary)
    (out/'index.html').write_text(render_summary(summary),encoding='utf-8',newline='\n')
    rows=[{'path':p.name,'sha256':digest(read_bytes(p)),'bytes':p.stat().st_size}
          for p in sorted(out.iterdir(),key=lambda item:item.name) if p.is_file()]
    write_json(out/'DEMO-MANIFEST.json',seal({'schema':'miw.dossier_manifest.v1',**BOUNDARY,'files':rows},'manifest_root'))
    return summary

def verify_dossier(folder:Path) -> dict:
    manifest=check_seal(read_json(folder/'DEMO-MANIFEST.json'),'manifest_root')
    require(manifest['schema']=='miw.dossier_manifest.v1' and all(manifest[k]==v for k,v in BOUNDARY.items()),'DOSSIER_SCHEMA_INVALID')
    exact_keys(manifest,{'schema','standing','authority_effect','files','manifest_root'})
    require(type(manifest['files']) is list,'DOSSIER_MANIFEST_ROWS')
    for row in manifest['files']:
        exact_keys(row,{'path','sha256','bytes'});require(type(row['bytes']) is int and row['bytes']>=0,'DOSSIER_MANIFEST_SIZE')
    expected={r['path'] for r in manifest['files']}|{'DEMO-MANIFEST.json'}
    require({p.name for p in folder.iterdir()}==expected,'DOSSIER_MEMBER_SET_MISMATCH')
    require(len(expected)==len(manifest['files'])+1,'DOSSIER_DUPLICATE_PATH')
    for row in manifest['files']:
        safe_relative(row['path']);require('/' not in row['path'],'DOSSIER_SUBDIRECTORY_UNSUPPORTED')
        data=read_bytes(folder/row['path']);require(digest(data)==row['sha256'] and len(data)==row['bytes'],'DOSSIER_MEMBER_MISMATCH')
    summary=check_seal(read_json(folder/'SUMMARY.json'),'summary_root')
    require(summary['schema']=='miw.turn4_scalar_demo.v1' and all(summary[k]==v for k,v in BOUNDARY.items()),'DOSSIER_SUMMARY_BOUNDARY_INVALID')
    exact_keys(summary,{'schema','standing','authority_effect','turn','examples','mutations','phases',
        'zucchini_validation','zucchini_live_cpp','scope_check_protected_roles','graph_completeness',
        'database','physical_inventory','independent_review','runtime_inputs','summary_root'})
    limits={'turn':4,'zucchini_validation':'THIS_DOSSIER_SYNTHETIC_FIXTURES_ONLY','zucchini_live_cpp':'NOT_RUN_BY_DOSSIER_GENERATOR',
            'scope_check_protected_roles':5,'graph_completeness':'PARTIAL_FULL_REQUALIFICATION_REQUIRED',
            'database':'SEPARATE_REFERENCE_ADAPTER_LIVE_NOT_RUN','physical_inventory':'NOT_VERIFIED',
            'independent_review':'NOT_PERFORMED','runtime_inputs':'No production data; synthetic examples only'}
    require(all(type(summary[k]) is type(v) and summary[k]==v for k,v in limits.items()),'DOSSIER_UNSUPPORTED_SUMMARY_CLAIM')
    require([e['name'] for e in summary['examples']]==['assembly','allocation'],'DOSSIER_EXAMPLE_SET_INVALID')
    checks=[]
    for e in summary['examples']:
        name=e['name'];c=read_json(folder/(name+'.contract.json'));s=read_bytes(folder/(name+'.source.py')).decode()
        p=read_json(folder/(name+'.proof.json'));checked=verify_source_proof(c,s,p);checks.append(checked)
        require(read_json(folder/(name+'.proof-check.json'))==checked,'DOSSIER_CHECK_RECORD_MISMATCH')
        for key in ['path_count','obligation_count','native_vc_count','residual_count','subject_root','proof_root']:
            require(e[key]==checked[key],'DOSSIER_PROOF_SUMMARY_MISMATCH')
        require(e['proof_outcome']==checked['outcome'],'DOSSIER_PROOF_SUMMARY_MISMATCH')
        recorded=check_seal(read_json(folder/(name+'.execution.json')),'execution_root')
        from .bdd import discover
        feature=read_bytes(folder/(name+'.feature')).decode()
        validate_execution_record(c,s,feature,recorded)
        discovery=discover(c,feature)
        require(recorded['discovery']==discovery and recorded['discovery_root']==discovery['discovery_root'],
                'DOSSIER_EXECUTION_DISCOVERY_MISMATCH')
        require(recorded['source_sha256']==digest(s.encode()) and recorded['contract_root']==root(c),'DOSSIER_EXECUTION_SUBJECT_MISMATCH')
        require(e['scenario_count']==len(recorded['runs']) and e['scenario_passes']==sum(r['status']=='PASSED' for r in recorded['runs']),
                'DOSSIER_TEST_SUMMARY_MISMATCH')
    require([m['id'] for m in summary['mutations']]==[m[0] for m in MUTANTS]+['ALWAYS_REFUSE'],'DOSSIER_MUTATION_SET_INVALID')
    mutant_checks=[]
    c=read_json(folder/'assembly.contract.json')
    for mutation in summary['mutations']:
        name=mutation['id'];s=read_bytes(folder/f'mutant.{name}.source.py').decode()
        p=read_json(folder/f'mutant.{name}.proof.json');checked=verify_source_proof(c,s,p);mutant_checks.append(checked)
        require(mutation['proof_outcome']==checked['outcome'] and mutation['residual_count']==checked['residual_count'],'DOSSIER_MUTATION_SUMMARY_MISMATCH')
        counterexample=check_seal(read_json(folder/f'mutant.{name}.counterexample.json'),'assessment_root')
        execution=read_json(folder/f'mutant.{name}.execution.json')
        validate_assessment_record(c,s,read_bytes(folder/'assembly.feature').decode(),mutation['target'],execution,counterexample)
        require(counterexample['source_sha256']==digest(s.encode()) and counterexample['contract_root']==root(c)
                and counterexample['target_requirement']==mutation['target'],'DOSSIER_COUNTEREXAMPLE_SUBJECT_MISMATCH')
        from .bdd import discover
        discovery=discover(c,read_bytes(folder/'assembly.feature').decode())
        require(counterexample['feature_sha256']==discovery['feature_sha256']
                and counterexample['discovery_root']==discovery['discovery_root'],'DOSSIER_COUNTEREXAMPLE_DISCOVERY_MISMATCH')
        require(counterexample['outcome']==mutation['counterexample_outcome'] and len(counterexample['failures'])==mutation['failed_assertions'],
                'DOSSIER_COUNTEREXAMPLE_SUMMARY_MISMATCH')
    # Discovery imports and links are re-derived from exact retained raw inputs.
    report_raw=read_bytes(folder/'zucchini.report.json');junit_raw=read_bytes(folder/'zucchini.junit.xml')
    imported=import_report(report_raw);binding=make_junit_binding(report_raw,junit_raw)
    require(read_json(folder/'zucchini.import.json')==imported,'DOSSIER_ZUCCHINI_IMPORT_MISMATCH')
    require(read_json(folder/'zucchini.binding.json')==binding,'DOSSIER_ZUCCHINI_BINDING_MISMATCH')
    require(read_json(folder/'zucchini.execution-link.json')==link_junit(report_raw,junit_raw,binding),'DOSSIER_ZUCCHINI_LINK_MISMATCH')
    require(read_bytes(folder/'index.html')==render_summary(summary).encode('utf-8'),'DOSSIER_HTML_PROJECTION_MISMATCH')
    phases=[]
    for e,checked in zip(summary['examples'],checks,strict=True):
        execution=read_json(folder/(e['name']+'.execution.json'))
        phases.extend([{'phase':'STATIC_PROOF_BUILT','example':e['name'],'source_execution':'NONE','proof_root':checked['proof_root']},
                       {'phase':'STATIC_PROOF_RECHECKED','example':e['name'],'source_execution':'NONE','check_root':checked['check_root']},
                       {'phase':'EXAMPLES_EXECUTED','example':e['name'],'execution_root':execution['execution_root']}])
    require(summary['phases']==phases,'DOSSIER_PHASE_BINDING_MISMATCH')
    assembly=read_json(folder/'assembly.contract.json')
    source=read_bytes(folder/'assembly.source.py');feature=read_bytes(folder/'assembly.feature')
    nodes=[{'id':'contract','kind':'REQUIREMENT','root':root(assembly)},
           {'id':'source','kind':'IMPLEMENTATION','root':digest(source)},
           {'id':'proof','kind':'CHECKED_PROOF','root':checks[0]['proof_root']},
           {'id':'scenarios','kind':'SCENARIO_SPECIFICATION','root':digest(feature)},
           {'id':'execution','kind':'EXECUTED_EXAMPLES','root':read_json(folder/'assembly.execution.json')['execution_root']},
           {'id':'zucchini','kind':'IMPORTED_DECLARATIONS','root':imported['import_root']},
           {'id':'database_boundary','kind':'OPEN_OBLIGATION','root':'UNBOUND'},
           {'id':'physical_inventory','kind':'EMPIRICAL_ASSUMPTION','root':'UNVERIFIED'}]
    edges=[{'dependency':a,'dependent':b,'relation':r} for a,b,r in
           [('contract','proof','CHECKS'),('source','proof','CHECKS'),('contract','scenarios','CHECKS'),
            ('scenarios','execution','OBSERVES'),('source','execution','OBSERVES'),('source','database_boundary','DEPENDS_ON')]]
    graph=make_graph(nodes,edges,'Inventory demonstrator plus named unresolved external boundaries')
    require(read_json(folder/'graph.json')==graph,'DOSSIER_GRAPH_BINDING_MISMATCH')
    require(read_json(folder/'impact.json')==impact(graph,['source'],graph['graph_root']),'DOSSIER_IMPACT_MISMATCH')

    return seal({'schema':'miw.dossier_check.v1',**BOUNDARY,'manifest_root':manifest['manifest_root'],
        'summary_root':summary['summary_root'],'native_proof_checks':checks,'mutant_proof_checks':mutant_checks,
        'observed_tests':'RECORDED_NOT_RERUN','record_consistency':'CHECKED_NOT_AUTHENTICATED','scope':'Exact bundled sources, not current production or upstream C++'},'dossier_check_root')
