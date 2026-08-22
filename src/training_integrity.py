"""Distributed training-step integrity controller.

This module is hardware-agnostic. It evaluates explicit worker observations and
produces deterministic recovery decisions. It does not claim live NVIDIA,
CUDA, NCCL, or production-cluster execution.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import hashlib
import json
from math import isfinite
from statistics import median
from typing import Iterable

EVIDENCE_STATE = "DETERMINISTIC_DISTRIBUTED_TRAINING_INTEGRITY_MODEL"


class ControllerState(str, Enum):
    CLOSED = "CLOSED"
    DEGRADED = "DEGRADED"
    OPEN = "OPEN"
    RECOVERING = "RECOVERING"


class StepAction(str, Enum):
    ALLOW = "ALLOW"
    QUARANTINE_RANKS = "QUARANTINE_RANKS"
    RETRY_WITH_BACKOFF = "RETRY_WITH_BACKOFF"
    ROLLBACK_CHECKPOINT = "ROLLBACK_CHECKPOINT"
    HALT = "HALT"


@dataclass(frozen=True)
class WorkerObservation:
    rank: int
    loss: float
    grad_norm: float
    step_time_ms: float
    heartbeat_age_ms: float = 0.0
    overflow: bool = False

    def __post_init__(self) -> None:
        if self.rank < 0:
            raise ValueError("rank must be non-negative")
        if not isfinite(self.step_time_ms) or self.step_time_ms <= 0:
            raise ValueError("step_time_ms must be finite and positive")
        if not isfinite(self.heartbeat_age_ms) or self.heartbeat_age_ms < 0:
            raise ValueError("heartbeat_age_ms must be finite and non-negative")


@dataclass(frozen=True)
class IntegrityPolicy:
    world_size: int
    minimum_healthy_fraction: float = 0.75
    stale_heartbeat_ms: float = 5_000.0
    grad_outlier_factor: float = 8.0
    trip_after_incidents: int = 3
    recovery_clean_steps: int = 2
    halt_after_open_steps: int = 4

    def __post_init__(self) -> None:
        if self.world_size <= 0:
            raise ValueError("world_size must be positive")
        if not 0.0 < self.minimum_healthy_fraction <= 1.0:
            raise ValueError("minimum_healthy_fraction must be within (0, 1]")
        for name in ("stale_heartbeat_ms", "grad_outlier_factor"):
            value = getattr(self, name)
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        for name in ("trip_after_incidents", "recovery_clean_steps", "halt_after_open_steps"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class StepDecision:
    step: int
    state: ControllerState
    action: StepAction
    healthy_ranks: tuple[int, ...]
    quarantined_ranks: tuple[int, ...]
    reasons: tuple[str, ...]
    healthy_fraction: float
    incident_streak: int
    clean_streak: int
    evidence_state: str = EVIDENCE_STATE

    def as_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["state"] = self.state.value
        data["action"] = self.action.value
        return data

    @property
    def digest(self) -> str:
        payload = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


class DistributedIntegrityController:
    """Stateful fail-closed controller for distributed training observations."""

    def __init__(self, policy: IntegrityPolicy) -> None:
        self.policy = policy
        self.state = ControllerState.CLOSED
        self.incident_streak = 0
        self.clean_streak = 0
        self.open_steps = 0
        self.last_step = -1

    @staticmethod
    def _robust_grad_limit(observations: tuple[WorkerObservation, ...], factor: float) -> float:
        finite_norms = sorted(
            observation.grad_norm
            for observation in observations
            if isfinite(observation.grad_norm) and observation.grad_norm >= 0
        )
        if not finite_norms:
            return 0.0
        center = median(finite_norms)
        deviations = [abs(value - center) for value in finite_norms]
        mad = median(deviations)
        if center == 0.0 and mad == 0.0:
            return 0.0
        return center + factor * mad if mad > 0 else center * factor

    def _classify(
        self, observations: tuple[WorkerObservation, ...]
    ) -> tuple[tuple[int, ...], tuple[int, ...], tuple[str, ...]]:
        grad_limit = self._robust_grad_limit(observations, self.policy.grad_outlier_factor)
        healthy: list[int] = []
        quarantined: list[int] = []
        reasons: list[str] = []

        for observation in observations:
            worker_reasons: list[str] = []
            if not isfinite(observation.loss):
                worker_reasons.append("NONFINITE_LOSS")
            if not isfinite(observation.grad_norm) or observation.grad_norm < 0:
                worker_reasons.append("NONFINITE_GRADIENT")
            elif grad_limit > 0 and observation.grad_norm > grad_limit:
                worker_reasons.append("GRADIENT_OUTLIER")
            if observation.overflow:
                worker_reasons.append("MIXED_PRECISION_OVERFLOW")
            if observation.heartbeat_age_ms > self.policy.stale_heartbeat_ms:
                worker_reasons.append("STALE_HEARTBEAT")

            if worker_reasons:
                quarantined.append(observation.rank)
                reasons.extend(f"rank={observation.rank}:{reason}" for reason in worker_reasons)
            else:
                healthy.append(observation.rank)

        return tuple(sorted(healthy)), tuple(sorted(quarantined)), tuple(sorted(reasons))

    def evaluate(
        self, step: int, observations: Iterable[WorkerObservation]
    ) -> StepDecision:
        if step <= self.last_step:
            raise ValueError("step must be strictly increasing")
        observed = tuple(observations)
        if len(observed) != self.policy.world_size:
            raise ValueError(
                f"expected {self.policy.world_size} observations, received {len(observed)}"
            )
        ranks = [observation.rank for observation in observed]
        if len(ranks) != len(set(ranks)):
            raise ValueError("worker ranks must be unique")
        expected = set(range(self.policy.world_size))
        if set(ranks) != expected:
            raise ValueError(f"worker ranks must exactly match {sorted(expected)}")

        self.last_step = step
        healthy, quarantined, reasons = self._classify(observed)
        healthy_fraction = len(healthy) / self.policy.world_size
        quorum = healthy_fraction >= self.policy.minimum_healthy_fraction
        incident = bool(quarantined)

        if incident:
            self.incident_streak += 1
            self.clean_streak = 0
        else:
            self.incident_streak = 0
            self.clean_streak += 1

        if self.state is ControllerState.OPEN:
            self.open_steps += 1
            if incident or not quorum:
                action = (
                    StepAction.HALT
                    if self.open_steps >= self.policy.halt_after_open_steps
                    else StepAction.ROLLBACK_CHECKPOINT
                )
            elif self.clean_streak >= self.policy.recovery_clean_steps:
                self.state = ControllerState.RECOVERING
                self.open_steps = 0
                action = StepAction.RETRY_WITH_BACKOFF
            else:
                action = StepAction.ROLLBACK_CHECKPOINT
        elif self.state is ControllerState.RECOVERING:
            if incident or not quorum:
                self.state = ControllerState.OPEN
                self.open_steps = 1
                action = StepAction.ROLLBACK_CHECKPOINT
            elif self.clean_streak >= self.policy.recovery_clean_steps + 1:
                self.state = ControllerState.CLOSED
                action = StepAction.ALLOW
            else:
                action = StepAction.RETRY_WITH_BACKOFF
        elif not quorum or self.incident_streak >= self.policy.trip_after_incidents:
            self.state = ControllerState.OPEN
            self.open_steps = 1
            action = StepAction.ROLLBACK_CHECKPOINT
        elif incident:
            self.state = ControllerState.DEGRADED
            action = StepAction.QUARANTINE_RANKS
        else:
            self.state = ControllerState.CLOSED
            action = StepAction.ALLOW

        return StepDecision(
            step=step,
            state=self.state,
            action=action,
            healthy_ranks=healthy,
            quarantined_ranks=quarantined,
            reasons=reasons,
            healthy_fraction=healthy_fraction,
            incident_streak=self.incident_streak,
            clean_streak=self.clean_streak,
        )
