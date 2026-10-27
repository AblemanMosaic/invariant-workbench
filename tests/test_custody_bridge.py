import tempfile,unittest
from pathlib import Path
from helpers import ROOT
from miw.custody_bridge import fixture_campaign
from miw.common import read_json,digest,read_bytes
class CustodyBridgeTests(unittest.TestCase):
    def test_actual_manager_candidate_bound_execution(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'campaign';r=fixture_campaign(ROOT,out)
            self.assertEqual(r['status'],'PASSED_FIXTURE_CUSTODY_INTEGRATION');self.assertTrue(r['candidate_receipt_bound']);self.assertTrue(r['canonical_source_unchanged'])
            self.assertTrue(r['stale_external_head_refused']);self.assertEqual(r['project_obligations_satisfied'],[])
            self.assertEqual(r['identity_status'],'PUBLISHED_FIXTURE_IDENTITIES_ONLY');self.assertEqual(r['production_signer'],'NOT_BOUND')
    def test_upstream_manager_closure_byte_exact(self):
        for row in read_json(ROOT/'vendor/ucm/TURN3-CLOSURE.json')['files']:
            self.assertEqual(digest(read_bytes(ROOT/'vendor/ucm'/row['path'])),row['sha256'])
