"""Approved contract data, kept distinct from implementation source."""
from __future__ import annotations
from copy import deepcopy
from typing import Any
from .common import require, exact_keys, identifier
from .restricted import parse_dnf, parse_term, evaluate_dnf, evaluate_term

FIELDS = {'schema','id','title','parameters','state','precondition','accept_when','accepted','refused',
          'decision_requirement','state_requirements','invariants','witnesses'}

def validate_contract(value: Any) -> dict:
    c = exact_keys(value, FIELDS)
    require(c['schema'] == 'miw.transition.v1', 'CONTRACT_SCHEMA_UNSUPPORTED')
    identifier(c['id']); identifier(c['decision_requirement'])
    require(type(c['title']) is str and bool(c['title']), 'CONTRACT_TITLE_REQUIRED')
    require(type(c['parameters']) is list and 1 <= len(c['parameters']) <= 12, 'PARAMETERS_INVALID')
    for p in c['parameters']: identifier(p); require(not p.startswith('out_'), 'RESERVED_NAME')
    require(len(set(c['parameters'])) == len(c['parameters']), 'DUPLICATE_PARAMETER')
    names = set(c['parameters'])
    require(type(c['state']) is list and 1 <= len(c['state']) <= 8, 'STATE_INVALID')
    require(all(type(s) is str and s in names for s in c['state']) and len(set(c['state'])) == len(c['state']),
            'STATE_INVALID')
    pre = parse_dnf(c['precondition'], names)
    require(len(pre) == 1, 'PRECONDITION_MUST_BE_CONJUNCTIVE')
    parse_dnf(c['accept_when'],names); parse_dnf(c['accept_when'],names,True)
    for branch in ['accepted','refused']:
        exact_keys(c[branch],set(c['state']))
        for expr in c[branch].values(): parse_term(expr,names)
    exact_keys(c['state_requirements'],set(c['state']))
    ids = [c['decision_requirement']]
    for rid in c['state_requirements'].values(): ids.append(identifier(rid))
    require(type(c['invariants']) is list and len(c['invariants']) <= 24, 'INVARIANTS_INVALID')
    for inv in c['invariants']:
        exact_keys(inv,{'id','formula'}); ids.append(identifier(inv['id']))
        clauses = parse_dnf(inv['formula'],names | {'out_'+s for s in c['state']})
        require(len(clauses) == 1 and bool(clauses[0]), 'INVARIANT_MUST_BE_NONEMPTY_CONJUNCTION')
    require(len(set(ids)) == len(ids), 'REQUIREMENT_ID_DUPLICATE')
    require(type(c['witnesses']) is list and 2 <= len(c['witnesses']) <= 32, 'NONVACUITY_WITNESSES_REQUIRED')
    observed = set()
    for witness in c['witnesses']:
        exact_keys(witness,{'inputs','accepted'})
        validate_inputs(c,witness['inputs'])
        require(type(witness['accepted']) is bool, 'WITNESS_STATUS_INVALID')
        flag,_ = expected_result(c,witness['inputs'])
        require(flag is witness['accepted'], 'WITNESS_DOES_NOT_MATCH_CONTRACT')
        observed.add(flag)
    require(observed == {False,True}, 'BOTH_ACCEPTANCE_AND_REFUSAL_WITNESSES_REQUIRED')
    return deepcopy(c)

def validate_inputs(contract: dict, values: Any) -> None:
    exact_keys(values,set(contract['parameters']))
    require(all(type(x) is int for x in values.values()), 'BUILTIN_INTEGER_INPUTS_REQUIRED')
    pre = parse_dnf(contract['precondition'],set(contract['parameters']))
    require(evaluate_dnf(pre,values), 'INPUT_PRECONDITION_NOT_MET')

def expected_result(contract: dict, values: dict) -> tuple[bool,dict]:
    """Independent specification evaluation, not subject-program execution."""
    validate_inputs(contract,values)
    names = set(contract['parameters'])
    accepted = evaluate_dnf(parse_dnf(contract['accept_when'],names),values)
    outputs = {s:evaluate_term(parse_term(expr,names),values)
               for s,expr in contract['accepted' if accepted else 'refused'].items()}
    return accepted,outputs

def requirement_ids(contract: dict) -> list[str]:
    return [contract['decision_requirement'],*contract['state_requirements'].values(),
            *(inv['id'] for inv in contract['invariants'])]
