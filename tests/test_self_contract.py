import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import ROOT
from miw.common import Refusal, read_json, seal
from miw.self_contract import explain_self_contract, validate_self_contract


class SelfContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = read_json(ROOT / 'constitutional/SELF-CONTRACT.json')
        cls.registry = read_json(ROOT / 'constitutional/OPERATION-REGISTRY.json')
        cls.plan = read_json(ROOT / 'constitutional/CTR-PLAN.json')

    def test_shipped_contract_validates_and_covers_every_court(self):
        result = validate_self_contract(self.contract, ROOT, self.registry, self.plan)
        self.assertEqual(result['status'], 'PASSED')
        self.assertEqual(result['courts_covered'], 9)
        self.assertEqual(result['guarantees'], 8)

    def test_explain_index_and_all_entry_kinds(self):
        index = explain_self_contract(self.contract, ROOT, self.registry, self.plan)
        self.assertEqual(index['result']['kind'], 'INDEX')
        cases = (
            ('G-BOUNDED-SELF-EXPLICATION', 'GUARANTEE'),
            ('NC-SELF-PROVING-TRUSTED-BASE', 'NONCLAIM'),
            ('A-HUMAN-SEMANTIC-APPROVAL', 'TRUSTED_ASSUMPTION'),
        )
        for item_id, kind in cases:
            with self.subTest(item_id=item_id):
                result = explain_self_contract(self.contract, ROOT, self.registry, self.plan, item_id)
                self.assertEqual(result['result']['kind'], kind)
                self.assertEqual(result['authority_effect'], 'NONE')
                self.assertIn('not law', result['claim_ceiling'])

    def test_unknown_item_refuses(self):
        with self.assertRaisesRegex(Refusal, 'SELF_CONTRACT_ITEM_UNKNOWN'):
            explain_self_contract(self.contract, ROOT, self.registry, self.plan, 'G-INVENTED')

    def test_tampered_contract_without_reseal_refuses(self):
        tampered = copy.deepcopy(self.contract)
        tampered['guarantees'][0]['claim'] = 'Everything is correct.'
        with self.assertRaisesRegex(Refusal, 'RECORD_ROOT_MISMATCH'):
            validate_self_contract(tampered, ROOT, self.registry, self.plan)

    def test_resealed_missing_code_path_refuses(self):
        changed = copy.deepcopy(self.contract)
        changed.pop('self_contract_root')
        changed['guarantees'][0]['enforcing_paths'] = ['src/miw/not-present.py']
        changed = seal(changed, 'self_contract_root')
        with self.assertRaisesRegex(Refusal, 'SELF_CONTRACT_CODE_PATH_MISSING'):
            validate_self_contract(changed, ROOT, self.registry, self.plan)

    def test_resealed_incomplete_court_coverage_refuses(self):
        changed = copy.deepcopy(self.contract)
        changed.pop('self_contract_root')
        for guarantee in changed['guarantees']:
            guarantee['court_ids'] = [court for court in guarantee['court_ids']
                                      if court != 'CTR-09-SELF-EXPLICATION']
        changed = seal(changed, 'self_contract_root')
        with self.assertRaisesRegex(Refusal, 'SELF_CONTRACT_COURT_COVERAGE_INCOMPLETE'):
            validate_self_contract(changed, ROOT, self.registry, self.plan)

    def test_cli_check_and_explain_create_sealed_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            check = Path(tmp) / 'check.json'
            explanation = Path(tmp) / 'explanation.json'
            base = [sys.executable, '-I', '-B', str(ROOT / 'tools/miw.py')]
            checked = subprocess.run(base + ['self-contract-check', '--out', str(check)],
                                     capture_output=True, text=True, timeout=30)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            explained = subprocess.run(base + ['explain', '--id', 'G-FAIL-CLOSED',
                                                '--out', str(explanation)],
                                       capture_output=True, text=True, timeout=30)
            self.assertEqual(explained.returncode, 0, explained.stderr)
            self.assertEqual(json.loads(check.read_text())['status'], 'PASSED')
            self.assertEqual(json.loads(explanation.read_text())['status'], 'EXPLAINED')


if __name__ == '__main__':
    unittest.main()
