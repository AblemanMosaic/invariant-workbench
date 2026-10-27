"""Structural, deterministic change explanations. No inferred semantic equivalence."""
from __future__ import annotations
from difflib import unified_diff
from .common import require,seal,root,digest,BOUNDARY
from .contracts import validate_contract

def explain_change(old_contract:dict,new_contract:dict,old_source:str,new_source:str)->dict:
    validate_contract(old_contract);validate_contract(new_contract)
    fields=[]
    for k in sorted(set(old_contract)|set(new_contract)):
        if old_contract.get(k)!=new_contract.get(k):
            risk=('PRECONDITION_CHANGED_POSSIBLE_DOMAIN_NARROWING' if k=='precondition' else
                  'BEHAVIORAL_CONTRACT_CHANGED' if k in {'accept_when','accepted','refused','invariants'} else
                  'INTERFACE_CHANGED' if k in {'parameters','state','id'} else 'SPECIFICATION_METADATA_CHANGED')
            fields.append({'field':k,'before':old_contract.get(k),'after':new_contract.get(k),'classification':risk})
    source_changed=old_source!=new_source
    return seal({'schema':'miw.change_explanation.v1',**BOUNDARY,
                 'before':{'contract_root':root(old_contract),'source_sha256':digest(old_source.encode())},
                 'after':{'contract_root':root(new_contract),'source_sha256':digest(new_source.encode())},
                 'contract_changes':fields,'implementation_changed':source_changed,
                 'source_diff':''.join(unified_diff(old_source.splitlines(True),new_source.splitlines(True),fromfile='before.py',tofile='after.py')),
                 'semantic_equivalence':'NOT_ESTABLISHED' if fields or source_changed else 'IDENTICAL_INPUT_BYTES',
                 'required_action':'FULL_REQUALIFICATION' if fields or source_changed else 'NO_CHANGED_INPUTS',
                 'proof_reuse':'NOT_AUTHORIZED','approval':'HUMAN_REQUIRED_FOR_CONTRACT_CHANGE' if fields else 'NO_CONTRACT_CHANGE',
                 'graph_completeness':'PARTIAL'})
