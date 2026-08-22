import math
import unittest

from src.training_integrity import (
    ControllerState,
    DistributedIntegrityController,
    IntegrityPolicy,
    StepAction,
    WorkerObservation,
)


def good(rank: int, *, grad: float = 1.0) -> WorkerObservation:
    return WorkerObservation(rank, loss=2.0, grad_norm=grad, step_time_ms=20.0)


class TrainingIntegrityTests(unittest.TestCase):
    def test_clean_quorum_allows_step_and_digest_is_deterministic(self):
        controller = DistributedIntegrityController(IntegrityPolicy(world_size=4))
        decision = controller.evaluate(0, [good(i) for i in range(4)])
        self.assertEqual(decision.action, StepAction.ALLOW)
        self.assertEqual(decision.state, ControllerState.CLOSED)
        self.assertEqual(len(decision.digest), 64)
        self.assertEqual(decision.digest, decision.digest)

    def test_single_nan_rank_is_quarantined_while_quorum_survives(self):
        controller = DistributedIntegrityController(IntegrityPolicy(world_size=4))
        observations = [good(i) for i in range(4)]
        observations[2] = WorkerObservation(2, loss=math.nan, grad_norm=1.0, step_time_ms=20)
        decision = controller.evaluate(0, observations)
        self.assertEqual(decision.action, StepAction.QUARANTINE_RANKS)
        self.assertEqual(decision.quarantined_ranks, (2,))
        self.assertIn("rank=2:NONFINITE_LOSS", decision.reasons)

    def test_lost_quorum_opens_and_requests_rollback(self):
        controller = DistributedIntegrityController(IntegrityPolicy(world_size=4))
        observations = [good(0), good(1)]
        observations += [
            WorkerObservation(2, loss=math.nan, grad_norm=1, step_time_ms=20),
            WorkerObservation(3, loss=2, grad_norm=math.inf, step_time_ms=20),
        ]
        decision = controller.evaluate(0, observations)
        self.assertEqual(decision.state, ControllerState.OPEN)
        self.assertEqual(decision.action, StepAction.ROLLBACK_CHECKPOINT)

    def test_repeated_single_rank_incidents_trip_even_with_quorum(self):
        controller = DistributedIntegrityController(
            IntegrityPolicy(world_size=4, trip_after_incidents=2)
        )
        for step in (0, 1):
            observations = [good(i) for i in range(4)]
            observations[3] = WorkerObservation(3, loss=math.nan, grad_norm=1, step_time_ms=20)
            decision = controller.evaluate(step, observations)
        self.assertEqual(decision.state, ControllerState.OPEN)
        self.assertEqual(decision.action, StepAction.ROLLBACK_CHECKPOINT)

    def test_open_controller_requires_clean_recovery_sequence(self):
        controller = DistributedIntegrityController(
            IntegrityPolicy(world_size=2, minimum_healthy_fraction=1.0, recovery_clean_steps=2)
        )
        bad = [good(0), WorkerObservation(1, loss=math.nan, grad_norm=1, step_time_ms=20)]
        self.assertEqual(controller.evaluate(0, bad).state, ControllerState.OPEN)
        first = controller.evaluate(1, [good(0), good(1)])
        second = controller.evaluate(2, [good(0), good(1)])
        third = controller.evaluate(3, [good(0), good(1)])
        self.assertEqual(first.action, StepAction.ROLLBACK_CHECKPOINT)
        self.assertEqual(second.state, ControllerState.RECOVERING)
        self.assertEqual(third.action, StepAction.ALLOW)
        self.assertEqual(third.state, ControllerState.CLOSED)

    def test_persistent_open_incident_halts(self):
        controller = DistributedIntegrityController(
            IntegrityPolicy(world_size=2, minimum_healthy_fraction=1.0, halt_after_open_steps=2)
        )
        bad = [good(0), WorkerObservation(1, loss=math.nan, grad_norm=1, step_time_ms=20)]
        first = controller.evaluate(0, bad)
        second = controller.evaluate(1, bad)
        self.assertEqual(first.action, StepAction.ROLLBACK_CHECKPOINT)
        self.assertEqual(second.action, StepAction.HALT)

    def test_outlier_and_stale_heartbeat_are_quarantined(self):
        controller = DistributedIntegrityController(IntegrityPolicy(world_size=5))
        observations = [good(0), good(1), good(2), good(3)]
        observations.append(
            WorkerObservation(4, loss=2, grad_norm=1000, step_time_ms=20, heartbeat_age_ms=6000)
        )
        decision = controller.evaluate(0, observations)
        self.assertEqual(decision.quarantined_ranks, (4,))
        self.assertTrue(any("GRADIENT_OUTLIER" in reason for reason in decision.reasons))
        self.assertTrue(any("STALE_HEARTBEAT" in reason for reason in decision.reasons))

    def test_topology_and_step_order_fail_closed(self):
        controller = DistributedIntegrityController(IntegrityPolicy(world_size=2))
        with self.assertRaises(ValueError):
            controller.evaluate(0, [good(0)])
        with self.assertRaises(ValueError):
            controller.evaluate(0, [good(0), good(0)])
        controller.evaluate(1, [good(0), good(1)])
        with self.assertRaises(ValueError):
            controller.evaluate(1, [good(0), good(1)])


if __name__ == "__main__":
    unittest.main()
