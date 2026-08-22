#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR=".verification-artifacts"
SCENARIO="${ARTIFACT_DIR}/training-integrity-scenario.json"
RECEIPT="${ARTIFACT_DIR}/training-integrity-scenario.receipt.json"
mkdir -p "${ARTIFACT_DIR}"

python -m compileall -q src tests scripts
python -m unittest discover -s tests -v | tee "${ARTIFACT_DIR}/unittest.txt"
python scripts/integrity_probe.py \
  --output "${SCENARIO}" \
  --receipt "${RECEIPT}" \
  | tee "${ARTIFACT_DIR}/integrity-probe.txt"

python - <<'PY'
import hashlib
import json
from pathlib import Path

scenario_path = Path('.verification-artifacts/training-integrity-scenario.json')
receipt_path = Path('.verification-artifacts/training-integrity-scenario.receipt.json')
scenario = json.loads(scenario_path.read_text(encoding='utf-8'))
receipt = json.loads(receipt_path.read_text(encoding='utf-8'))

actions = [row['action'] for row in scenario['timeline']]
assert actions == scenario['expected_actions']
assert scenario['timeline'][2]['state'] == 'OPEN'
assert scenario['timeline'][-1]['state'] == 'CLOSED'
assert scenario['timeline'][-1]['action'] == 'ALLOW'
assert scenario['evidence_state'] == 'DETERMINISTIC_DISTRIBUTED_TRAINING_INTEGRITY_MODEL'
actual = hashlib.sha256(scenario_path.read_bytes()).hexdigest()
assert receipt['artifact_sha256'] == actual
assert receipt['verified_state'] == 'RECOVERY_STATE_MACHINE_EXECUTED'
assert receipt['terminal_state'] == 'CLOSED'
print(json.dumps({
    'elite_core': 'PASS',
    'actions': actions,
    'terminal_state': receipt['terminal_state'],
    'artifact_sha256': actual,
}, indent=2))
PY
