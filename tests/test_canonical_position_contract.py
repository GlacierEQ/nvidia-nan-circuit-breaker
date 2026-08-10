import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = json.loads((ROOT / "machine" / "excellence-state.json").read_text(encoding="utf-8"))
POSITION = json.loads((ROOT / "machine" / "canonical-position.json").read_text(encoding="utf-8"))
CAPABILITIES = json.loads((ROOT / "machine" / "capabilities.json").read_text(encoding="utf-8"))
TARGET = json.loads((ROOT / "machine" / "target-contract.json").read_text(encoding="utf-8"))


class CanonicalPositionContractTests(unittest.TestCase):
    def test_machine_contract_is_valid_and_current(self):
        self.assertEqual(TARGET["schema"], "glaciereq.repo-target-contract.v1")
        self.assertEqual(TARGET["identity"]["repository_id"], STATE["repository"])
        self.assertEqual(TARGET["current"]["principal_state"], "EVOLVING")
        self.assertIn("latched OPEN state", TARGET["target"]["success"][1])

    def test_evolving_state_is_gate_complete(self):
        self.assertEqual(STATE["principal_state"], "EVOLVING")
        self.assertEqual(STATE["gates"]["CANONICAL_POSITION_RESOLVED"]["status"], "PASS")
        self.assertEqual(STATE["gates"]["EVOLUTION_CURSOR_DEFINED"]["status"], "PASS")
        self.assertEqual(STATE["canonical_position_ref"], "machine/canonical-position.json")

    def test_identity_lineage_and_specialist_ownership_are_preserved(self):
        self.assertEqual(POSITION["canonical_identity"], "nan-circuit-breaker")
        policy = POSITION["integration_policy"]
        self.assertTrue(policy["preserve_repository_identity"])
        self.assertTrue(policy["preserve_lineage"])
        self.assertTrue(policy["absorption_requires_functional_equivalence"])
        self.assertTrue(policy["absorption_requires_proof_equivalence"])

    def test_capabilities_match_implemented_latched_breaker(self):
        self.assertEqual(CAPABILITIES["capability_family"], "nonfinite_training_circuit_breaker")
        capabilities = set(CAPABILITIES["capabilities"])
        self.assertIn("consecutive-nonfinite-trip-threshold", capabilities)
        self.assertIn("latched-open-execution-block", capabilities)
        self.assertIn("explicit-authorized-breaker-reset", capabilities)
        self.assertIn("malformed-reset-refusal", capabilities)
        self.assertNotIn("hyper-scaling", capabilities)

    def test_gradient_edge_is_complementary_not_integrated(self):
        self.assertEqual(POSITION["relationships"][0]["repository"], "GlacierEQ/nvidia-gradient-integrity-quorum")
        self.assertEqual(POSITION["relationships"][0]["integration_state"], "NOT_CLAIMED")

    def test_public_boundary_is_preserved(self):
        self.assertIn("no NVIDIA affiliation", POSITION["nonclaims"])
        self.assertIn("No NVIDIA adoption", CAPABILITIES["truth_boundary"])


if __name__ == "__main__":
    unittest.main()
