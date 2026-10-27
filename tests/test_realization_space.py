import copy
import json
import unittest
from pathlib import Path

from helpers import ROOT
from miw.common import Refusal, read_json
from miw.realization_space import (
    lower_configuration, select_configuration, validate_bundle,
    validate_contract, validate_registry,
)


class RealizationSpaceTests(unittest.TestCase):
    def setUp(self):
        self.contract_path=ROOT/'schemas/INVARIANT-EVIDENCE-SPACE-CONTRACT.json'
        self.registry_path=ROOT/'schemas/INVARIANT-WORKBENCH-REALIZER-REGISTRY.json'
        self.dictionary_path=ROOT/'schemas/INVARIANT-WORKBENCH-CAPABILITY-DICTIONARY.json'
        self.contract=read_json(self.contract_path);self.registry=read_json(self.registry_path);self.dictionary=read_json(self.dictionary_path)

    def test_bundle_validates_and_vocabularies_are_distinct(self):
        checked=validate_bundle(self.contract_path,self.registry_path,self.dictionary_path)
        operations=set(self.contract['operations'])
        realizer_caps={x['id'] for x in self.dictionary['capabilities']}
        self.assertFalse(operations & realizer_caps)
        self.assertEqual(checked['contract']['axis_count'],4)

    def test_shipped_examples_validate_under_draft_2020_12(self):
        from jsonschema import Draft202012Validator
        contract_schema=read_json(ROOT/'schemas/invariant-evidence-space-contract-v0.1.schema.json')
        registry_schema=read_json(ROOT/'schemas/workbench-realizer-registry-v0.1.schema.json')
        self.assertEqual(list(Draft202012Validator(contract_schema).iter_errors(self.contract)),[])
        self.assertEqual(list(Draft202012Validator(registry_schema).iter_errors(self.registry)),[])

    def test_canonicalization_vectors_and_float_refusal(self):
        from miw.common import canonical_bytes
        vectors=read_json(ROOT/'schemas/RSC-CANONICALIZATION-VECTORS.json')['vectors']
        for vector in vectors:
            self.assertEqual(canonical_bytes(vector['value']).decode('utf-8'),vector['canonical_utf8'])
        value=copy.deepcopy(self.contract);value['axes'][0]['default']=1.25
        with self.assertRaisesRegex(Refusal,'RSC_FLOAT_REFUSED'):validate_contract(value)

    def test_selection_is_stable_and_locked_promotion_refuses(self):
        one=select_configuration(self.contract,{'LANE':'PROOF_RECHECK'})
        two=select_configuration(self.contract,{'LANE':'PROOF_RECHECK'})
        self.assertEqual(one,two)
        with self.assertRaisesRegex(Refusal,'RSC_AXIS_LOCKED'):
            select_configuration(self.contract,{'EVIDENCE_PROMOTION':True})

    def test_undeclared_is_not_unsupported(self):
        selection=select_configuration(self.contract)
        lowered=lower_configuration(self.contract,selection,self.registry,self.dictionary,
                                    target_id='OBLIGATION_BOARD',profile_id='MIW_MINIMAL')
        self.assertEqual(lowered['result'],'REFUSED')
        self.assertEqual(lowered['resolutions'][1]['code'],'RSC_CAPABILITY_UNDECLARED')

    def test_unknown_capability_refuses(self):
        registry=copy.deepcopy(self.registry)
        registry['profiles'][0]['realizer_capabilities']['INVENTED']={'status':'SUPPORTED','standing':'DECLARED'}
        with self.assertRaisesRegex(Refusal,'RSC_CAPABILITY_UNKNOWN'):
            validate_registry(registry,self.dictionary)

    def test_immediate_simulation_and_adaptive_determinism_refuse(self):
        value=copy.deepcopy(self.contract);axis=value['axes'][0]
        axis['state_effect']='SIMULATION_RULE';axis['apply_mode']='IMMEDIATE'
        with self.assertRaisesRegex(Refusal,'RSC_APPLY_MODE_REFUSED'):validate_contract(value)
        value=copy.deepcopy(self.contract);axis=value['axes'][0]
        axis['ownership']='ADAPTIVE';axis['mutability']='FRAME';axis['replay_effect']='SIMULATION_DETERMINISM'
        with self.assertRaisesRegex(Refusal,'RSC_REPLAY_DETERMINISM_REFUSED'):validate_contract(value)

    def test_measured_capability_requires_evidence_identity(self):
        registry=copy.deepcopy(self.registry)
        registry['profiles'][0]['realizer_capabilities']['OBLIGATION_LEDGER']['standing']='MEASURED'
        with self.assertRaisesRegex(Refusal,'RSC_MEASURED_EVIDENCE_REQUIRED'):
            validate_registry(registry,self.dictionary)

