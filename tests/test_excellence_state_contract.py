import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = json.loads((ROOT / "machine" / "excellence-state.json").read_text(encoding="utf-8"))
POSITION = json.loads((ROOT / "machine" / "apex-position.json").read_text(encoding="utf-8"))
CAPABILITIES = json.loads((ROOT / "machine" / "capabilities.json").read_text(encoding="utf-8"))
TARGET = json.loads((ROOT / "machine" / "target-contract.json").read_text(encoding="utf-8"))


class ExcellenceStateContractTests(unittest.TestCase):
    def test_state_is_evolving_and_apex_positioned(self):
        self.assertEqual(STATE["principal_state"], "EVOLVING")
        self.assertEqual(STATE["gates"]["APEX_POSITION_ACTIVE"]["status"], "PASS")
        self.assertEqual(STATE["gates"]["DISTRIBUTED_INTEGRITY_IMPLEMENTED"]["status"], "PASS")
        self.assertEqual(STATE["position_ref"], "machine/apex-position.json")

    def test_position_matches_source_capability(self):
        self.assertEqual(POSITION["repository"], STATE["repository"])
        self.assertEqual(POSITION["identity"], "distributed-training-integrity-controller")
        self.assertIn("rank quarantine for non-finite loss or gradients", POSITION["capabilities"])
        self.assertIn("bounded clean-step recovery sequence", POSITION["capabilities"])
        self.assertIn("persistent-open halt escalation", POSITION["capabilities"])

    def test_capability_manifest_projects_new_runtime(self):
        self.assertEqual(CAPABILITIES["capability_family"], "distributed_training_integrity")
        projected = set(CAPABILITIES["capabilities"])
        self.assertIn("healthy-quorum-calculation", projected)
        self.assertIn("checkpoint-rollback-decision", projected)
        self.assertIn("receipt-producing-recovery-scenario", projected)

    def test_target_requires_recovery_and_receipt_proof(self):
        required = set(TARGET["promotion"]["required_tests"])
        self.assertIn("distributed_integrity_recovery", required)
        self.assertIn("apex_position_contract", required)
        self.assertIn("receipt_verification", required)
        self.assertTrue(TARGET["promotion"]["require_repository_owned_ci"])

    def test_evolution_cursor_points_forward(self):
        self.assertTrue(STATE["evolution_cursor"].startswith("next:"))
        self.assertIn("gradient-quorum-adapter", STATE["evolution_cursor"])
        self.assertTrue(POSITION["next_capability_vector"])


if __name__ == "__main__":
    unittest.main()
