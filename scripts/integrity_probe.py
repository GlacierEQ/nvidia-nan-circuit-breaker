#!/usr/bin/env python3
"""Execute a deterministic distributed-training integrity scenario and emit a receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.training_integrity import (  # noqa: E402
    DistributedIntegrityController,
    IntegrityPolicy,
    WorkerObservation,
)


def good(rank: int) -> WorkerObservation:
    return WorkerObservation(rank, loss=2.0, grad_norm=1.0, step_time_ms=20.0)


def execute() -> dict[str, object]:
    policy = IntegrityPolicy(
        world_size=4,
        minimum_healthy_fraction=0.75,
        trip_after_incidents=2,
        recovery_clean_steps=2,
        halt_after_open_steps=4,
    )
    controller = DistributedIntegrityController(policy)
    timeline = []

    timeline.append(controller.evaluate(0, [good(i) for i in range(4)]).as_dict())

    bad_rank = [good(i) for i in range(4)]
    bad_rank[3] = WorkerObservation(3, loss=math.nan, grad_norm=1.0, step_time_ms=20.0)
    timeline.append(controller.evaluate(1, bad_rank).as_dict())
    timeline.append(controller.evaluate(2, bad_rank).as_dict())

    timeline.append(controller.evaluate(3, [good(i) for i in range(4)]).as_dict())
    timeline.append(controller.evaluate(4, [good(i) for i in range(4)]).as_dict())
    timeline.append(controller.evaluate(5, [good(i) for i in range(4)]).as_dict())

    return {
        "schema": "glaciereq.nvidia-training-integrity-scenario.v1",
        "evidence_state": "DETERMINISTIC_DISTRIBUTED_TRAINING_INTEGRITY_MODEL",
        "policy": {
            "world_size": policy.world_size,
            "minimum_healthy_fraction": policy.minimum_healthy_fraction,
            "trip_after_incidents": policy.trip_after_incidents,
            "recovery_clean_steps": policy.recovery_clean_steps,
            "halt_after_open_steps": policy.halt_after_open_steps,
        },
        "timeline": timeline,
        "expected_actions": [
            "ALLOW",
            "QUARANTINE_RANKS",
            "ROLLBACK_CHECKPOINT",
            "ROLLBACK_CHECKPOINT",
            "RETRY_WITH_BACKOFF",
            "ALLOW",
        ],
        "claims_not_established": [
            "NVIDIA hardware execution",
            "CUDA or NCCL integration",
            "live distributed training control",
            "checkpoint restoration on a production cluster",
            "measured model convergence improvement",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    payload = execute()
    actions = [entry["action"] for entry in payload["timeline"]]
    if actions != payload["expected_actions"]:
        raise SystemExit(f"unexpected state-machine path: {actions}")

    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()

    receipt = {
        "schema": "glaciereq.nvidia-training-integrity-receipt.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repository": os.environ.get(
            "GITHUB_REPOSITORY", "GlacierEQ/nvidia-nan-circuit-breaker"
        ),
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "artifact": str(args.output),
        "artifact_sha256": digest,
        "verified_state": "RECOVERY_STATE_MACHINE_EXECUTED",
        "terminal_state": payload["timeline"][-1]["state"],
        "terminal_action": payload["timeline"][-1]["action"],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
