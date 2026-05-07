import json
import subprocess
import sys
from pathlib import Path

from eva.common import atomic_write_json, ensure_vault
from eva.proposers.propose_patches import record_outcome


def _proposal(pid='p1'):
    return {'id': pid, 'kind': 'tool_failure_triage', 'title': 'Classify', 'status': 'pending'}


def test_record_outcome_supports_approved_deferred_and_terminal_states(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(vault / 'proposals' / 'pending' / 'p1.json', _proposal('p1'))
    approved = record_outcome('p1', 'approved', vault, 'ok')
    assert approved == vault / 'proposals' / 'approved' / 'p1.json'
    data = json.loads(approved.read_text())
    assert data['status'] == 'approved'
    assert data['operator_note'] == 'ok'
    applied = record_outcome('p1', 'applied', vault, 'done')
    assert applied == vault / 'proposals' / 'applied' / 'p1.json'
    assert json.loads(applied.read_text())['previous_status'] == 'approved'


def test_record_outcome_rejects_unknown_state(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(vault / 'proposals' / 'pending' / 'p1.json', _proposal('p1'))
    result = subprocess.run([sys.executable, '-m', 'eva.proposers.propose_patches', '--vault', str(vault), '--record-outcome', 'maybe', '--proposal-id', 'p1'], text=True, capture_output=True)
    assert result.returncode != 0
