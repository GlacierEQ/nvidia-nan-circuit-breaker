# AGENTS.md — nvidia-nan-circuit-breaker

**Company:** NVIDIA
**Domain:** Datacenter Compute & GPU Cluster Orchestration

## Quick Rules
- **Test command:** `PYTHONPATH=src pytest tests/ -v`
- **Lint:** `ruff check src/ tests/`
- **No drive-by edits** — load the skill first.

## Architecture
- `src/nvidia_nan_circuit_breaker/core.py` — Domain logic (Datacenter Compute & GPU Cluster Orchestration)
- `tests/` — Verified test suite
- `.github/workflows/ci.yml` — Enforced CI pipeline
