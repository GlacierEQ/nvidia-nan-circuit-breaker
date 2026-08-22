# NVIDIA-Class Distributed Training Integrity Controller

Independent GlacierEQ portfolio engineering for distributed-training numerical integrity. The repository began as a focused NaN circuit breaker and now preserves that primitive while adding a quorum-aware recovery controller around multi-worker training steps.

This project is **not affiliated with, endorsed by, or operated by NVIDIA**. It does not claim proprietary NVIDIA access, live CUDA/NCCL execution, production-cluster deployment, or measured convergence improvement.

## What is implemented

### Local fail-closed primitive

`src/nan_breaker.py` retains the small latched breaker: consecutive non-finite observations trip `OPEN`, protected work remains blocked, and recovery requires explicit reset.

### Distributed integrity controller

`src/training_integrity.py` adds a deterministic multi-rank control plane with:

- exact world-topology and rank uniqueness validation;
- non-finite loss and gradient quarantine;
- mixed-precision overflow quarantine;
- robust median/MAD gradient-outlier detection;
- stale-heartbeat detection;
- healthy-quorum calculation;
- `CLOSED → DEGRADED → OPEN → RECOVERING → CLOSED` state transitions;
- repeated-incident escalation even while quorum still survives;
- checkpoint-rollback decisions when quorum is lost or the breaker trips;
- persistent-OPEN escalation to `HALT`;
- bounded clean-step recovery before normal execution resumes;
- structured reasons, quarantined ranks, healthy fraction, and deterministic decision digests.

The controller produces **decisions**, not fictional infrastructure effects. `ROLLBACK_CHECKPOINT` means the modeled control decision is rollback; this repository does not claim that a production checkpoint was restored.

## Executable proof

Run the complete repository-owned proof:

```bash
bash scripts/ci/verify_elite_core.sh
```

That path compiles the Python surfaces, executes the full unit/adversarial suite, runs a six-step failure-and-recovery scenario, and verifies a content-hashed receipt.

The scenario deliberately proves this progression:

```text
ALLOW
→ QUARANTINE_RANKS
→ ROLLBACK_CHECKPOINT
→ ROLLBACK_CHECKPOINT
→ RETRY_WITH_BACKOFF
→ ALLOW
```

GitHub Actions executes the Python proof on **3.11, 3.12, and 3.13**, while preserving the repository's native C test lane.

## Proof surfaces

| Surface | Role |
|---|---|
| `src/nan_breaker.py` | focused local non-finite latch |
| `src/training_integrity.py` | distributed integrity/recovery state machine |
| `tests/test_training_integrity.py` | quorum, quarantine, trip, rollback, recovery, halt, topology adversarial proof |
| `tests/test_adversarial.py` | inherited adversarial regression surface |
| `scripts/integrity_probe.py` | deterministic recovery scenario + content-hashed receipt |
| `scripts/ci/verify_elite_core.sh` | repository-owned end-to-end verification path |
| `machine/apex-position.json` | evolving capability position and next composition vector |
| `.github/workflows/tests.yml` | cross-version Python + native-C CI |

## Quality direction

`GlacierEQ/xai-colossus-cooling` is used as a **quality benchmark, not a source template**: meaningful domain runtime, adversarial proof, failure/recovery behavior, executable receipts, and honest evidence boundaries. This leaf implements those laws in the distributed-training-integrity domain instead of copying cooling mechanisms.

The next coherent capability vector is optional composition with `GlacierEQ/nvidia-gradient-integrity-quorum`, checkpoint provenance verification, replayable incident traces, and state-machine fuzzing. Specialist repositories remain distinct unless composition preserves or exceeds their capability and proof.

## Evidence boundary

Established here: deterministic control logic and repository-owned proof over explicit synthetic observations.

Not established here: NVIDIA adoption, CUDA/NCCL integration, live GPU telemetry, production checkpoint restoration, production distributed-training authority, measured hardware performance, or measured model-quality improvement.
