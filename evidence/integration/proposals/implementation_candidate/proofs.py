"""Source-derived proof obligations checked by the unchanged UCM c4 kernel.

No test, imported report or AI statement enters this proof path. The AST
frontend and its relation to Python remain explicit trusted implementation.
"""
from __future__ import annotations
from typing import Any
from uclop.deductive_proofs import make_contract, prove_contract, verify_proof, evidence_subject
from uclop.obligations import inventory, conserve
from uclop.checkers import make_evidence_material, evaluate_evidence
from .common import BOUNDARY, require, root, seal, check_seal, digest, exact_keys, implementation_identity
from .contracts import validate_contract
from .restricted import lower_source, parse_dnf, parse_term, conjunction, sub_atom

SCOPE = 'All paths of the accepted loop-free Python subset over valid built-in integer inputs'

TRUST = [
    'Approved requirement meaning and independent approval are human responsibilities.',
    'The new restricted Python AST frontend and path-to-contract lowering are trusted, not formally proved.',
    'UCM c4 validation, VC generation, canonical binding and certificate checking are trusted inherited code.',
    'CPython built-in integer, Boolean and tuple semantics are assumed; custom objects and bool-as-int inputs are rejected.',
    'Interpreter/compiler/OS/hardware correctness and resource exhaustion are not proved.',
    'No database, C++, concurrency, remote API or physical inventory guarantee is established.'
]

def derive_obligations(contract: dict, source: str) -> dict:
    c = validate_contract(contract)
    lowered = lower_source(source,c['id'],c['parameters'],c['state'])
    identity = implementation_identity()
    subject = {'schema':'miw.proof_subject.v1','source_sha256':digest(source.encode('utf-8')),
               'contract_root':root(c),'engine_root':identity['engine_root'],
               'language':lowered['language']}
    subject_root = root(subject)
    names=set(c['parameters'])
    pre = parse_dnf(c['precondition'],names)[0]
    variables=[{'name':n,'sort':'INT'} for n in sorted(names)]
    rows=[]
    def emit(path:dict, rid:str, category:str, guard:list, post:dict) -> None:
        oid=f'o{len(rows):04d}'
        native = make_contract(contract_id=c['id']+'_'+oid,subject_root=subject_root,
            obligation_id=oid,variables=variables,assumptions=[],
            precondition=conjunction(pre+path['guards']+guard),body=[],postcondition=post)
        rows.append({'id':oid,'requirement':rid,'path_id':path['path_id'],'category':category,'contract':native})
    for path in lowered['paths']:
        # An accepted path must exclude all refusal cases, and vice versa.
        opposites=parse_dnf(c['accept_when'],names,negate=path['accepted'])
        # Explicit always-true decision property if the opposite is syntactically empty.
        if not opposites:
            emit(path,c['decision_requirement'],'DECISION',[],{'op':'EQ','args':[{'op':'INT','value':0}]*2})
        for opposite in opposites:
            emit(path,c['decision_requirement'],'DECISION',opposite,
                 {'op':'LT','args':[{'op':'INT','value':0},{'op':'INT','value':0}]})
        expected=c['accepted' if path['accepted'] else 'refused']
        for name in c['state']:
            emit(path,c['state_requirements'][name],'EXACT_STATE',[],
                 {'op':'EQ','args':[path['outputs'][name],parse_term(expected[name],names)]})
        substitutions={'out_'+s:path['outputs'][s] for s in c['state']}
        for inv in c['invariants']:
            atoms=parse_dnf(inv['formula'],names|set(substitutions))[0]
            emit(path,inv['id'],'INVARIANT',[],conjunction([sub_atom(a,substitutions) for a in atoms]))
    return {'subject':subject,'subject_root':subject_root,'lowering':lowered,'obligations':rows}

def _conservation(derived:dict, proof_rows:list[dict]) -> dict:
    obligations=[]
    for row in derived['obligations']:
        obligations.append({'id':row['id'],'kind':'SAFETY','statement':row['requirement']+':'+row['category'],
            'source_ref':row['path_id'],'assumptions':[],'required_evidence':['NATIVE_DEDUCTIVE_PROOF'],
            'severity':'HIGH','evidence_subject':evidence_subject(row['contract'])})
    unresolved=[o for o,p in zip(obligations,proof_rows,strict=True) if p['bundle']['outcome']!='PROVED']
    source=inventory(obligations,derived['subject_root']); target=inventory(unresolved,derived['subject_root'])
    edges=[]; receipts={}; materials={}
    for obligation,row,proof in zip(obligations,derived['obligations'],proof_rows,strict=True):
        if proof['bundle']['outcome']=='PROVED':
            material=make_evidence_material('EXACT_NATIVE_DEDUCTIVE_PROOF_V1',
                obligation_id=obligation['id'],disposition='DISCHARGED',
                source_inventory_root=source['inventory_root'],target_inventory_root=target['inventory_root'],
                target_obligation_ids=[],evidence_subject=obligation['evidence_subject'],
                payload={'contract':row['contract'],'proof_bundle':proof['bundle']})
            receipt=evaluate_evidence(material,source_inventory_root=source['inventory_root'],
                target_inventory_root=target['inventory_root'],source_obligation=obligation,
                target_obligations=[],disposition='DISCHARGED')
            receipts[receipt['receipt_root']]=receipt; materials[material['evidence_root']]=material
            disposition='DISCHARGED'; tos=[]; refs=[receipt['receipt_root']]
        else:
            disposition='RESIDUAL';tos=[obligation['id']];refs=[]
        edges.append({'from_id':obligation['id'],'to_ids':tos,'disposition':disposition,
                      'edge_kind':'CHECKS','evidence_refs':refs,'reason':'Exact native check or preserved unresolved obligation'})
    mapping=conserve(source,target,edges,pass_id='MIW_TURN2_NATIVE',evidence_records=receipts,evidence_materials=materials)
    return {'source_inventory':source,'residual_inventory':target,'map':mapping,'receipts':list(receipts.values())}

def prove_source(contract:dict, source:str) -> dict:
    derived=derive_obligations(contract,source)
    rows=[]
    for row in derived['obligations']:
        bundle=prove_contract(row['contract'])
        checked=verify_proof(row['contract'],bundle)
        rows.append({'id':row['id'],'bundle':bundle,'check':checked})
    conservation=_conservation(derived,rows)
    status='CHECKED_SOURCE_PROOF' if all(r['bundle']['outcome']=='PROVED' for r in rows) else 'UNKNOWN_PROOF'
    return seal({'schema':'miw.source_proof.v1',**BOUNDARY,'subject':derived['subject'],
        'subject_root':derived['subject_root'],'lowering':derived['lowering'],
        'obligations':derived['obligations'],'proofs':rows,'conservation':conservation,
        'outcome':status,'trust':TRUST,'source_execution':'NONE',
        'proof_scope':SCOPE},'proof_root')

def verify_source_proof(contract:dict,source:str,record:Any) -> dict:
    record=check_seal(record,'proof_root')
    exact_keys(record,{'schema','standing','authority_effect','subject','subject_root','lowering','obligations',
        'proofs','conservation','outcome','trust','source_execution','proof_scope','proof_root'})
    require(record['schema']=='miw.source_proof.v1' and all(record[k]==v for k,v in BOUNDARY.items()),'PROOF_BOUNDARY_MISMATCH')
    require(record['trust']==TRUST and record['source_execution']=='NONE' and record['proof_scope']==SCOPE,'PROOF_TRUST_BOUNDARY_MISMATCH')
    derived=derive_obligations(contract,source)
    for key in ['subject','subject_root','lowering','obligations']:
        require(record[key]==derived[key],'PROOF_REDERIVATION_MISMATCH',detail=key)
    require(type(record['proofs']) is list and len(record['proofs'])==len(derived['obligations']), 'PROOF_OBLIGATION_COUNT_MISMATCH')
    outcomes=[]
    for row,p in zip(derived['obligations'],record['proofs'],strict=True):
        exact_keys(p,{'id','bundle','check'});require(p['id']==row['id'],'PROOF_OBLIGATION_ORDER_MISMATCH')
        checked=verify_proof(row['contract'],p['bundle'])
        require(p['check']==checked,'PROOF_CHECK_MISMATCH')
        outcomes.append(checked['outcome'])
    conservation=_conservation(derived,record['proofs'])
    require(record['conservation']==conservation,'OBLIGATION_CONSERVATION_MISMATCH')
    status='CHECKED_SOURCE_PROOF' if all(x=='PROVED' for x in outcomes) else 'UNKNOWN_PROOF'
    require(record['outcome']==status,'PROOF_OUTCOME_MISMATCH')
    return seal({'schema':'miw.source_proof_check.v1',**BOUNDARY,'proof_root':record['proof_root'],
        'subject_root':derived['subject_root'],'outcome':status,'path_count':len(derived['lowering']['paths']),
        'obligation_count':len(outcomes),'native_vc_count':sum(len(p['bundle']['proofs']) for p in record['proofs']),
        'residual_count':len(conservation['residual_inventory']['obligations']),
        'source_execution':'NONE'},'check_root')
