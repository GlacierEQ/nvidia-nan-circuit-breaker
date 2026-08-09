#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nan_breaker import NanCircuitBreaker, BreakerState

def main() -> int:
    b = NanCircuitBreaker(trip_after=3)
    b.observe(False); b.observe(False); b.observe(False)
    open_blocks = b.state is BreakerState.OPEN and not b.allow_step()
    b.reset("reset:ops")
    closed = b.allow_step()
    out = {"tripped": open_blocks, "reset_allows": closed, "ok": open_blocks and closed}
    print(json.dumps(out, sort_keys=True))
    return 0 if out["ok"] else 1
if __name__ == "__main__":
    raise SystemExit(main())
