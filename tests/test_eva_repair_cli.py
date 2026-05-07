import json
import subprocess
import sys
from pathlib import Path

from eva.common import atomic_write_json, ensure_vault


def _proposal(pid='p1', kind='tool_failure_triage'):
    return {'id': pid, 'kind': kind, 'title': 'Triage', 'status':'pending', 'evidence': []}


def test_eva_repair_cli_help_and_draft_all(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(vault / 'proposals' / 'pending' / 'p1.json', _proposal())
    help_result = subprocess.run([sys.executable, '-m', 'eva.repair.cli', '--help'], text=True, capture_output=True, check=True)
    assert 'eva-repair' in help_result.stdout
    result = subprocess.run([sys.executable, '-m', 'eva.repair.cli', 'draft-all', '--vault', str(vault), '--write', '--json'], text=True, capture_output=True, check=True)
    data = json.loads(result.stdout)
    assert data['count'] == 1
    assert list((vault / 'repairs' / 'drafts').glob('*.json'))


def test_eva_repair_cli_approve_moves_proposal(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(vault / 'proposals' / 'pending' / 'p1.json', _proposal())
    subprocess.run([sys.executable, '-m', 'eva.repair.cli', 'approve', 'p1', '--vault', str(vault), '--note', 'approved'], check=True)
    assert (vault / 'proposals' / 'approved' / 'p1.json').exists()



def test_eva_repair_cli_reject_and_defer_move_proposals(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(vault / 'proposals' / 'pending' / 'p1.json', _proposal('p1'))
    atomic_write_json(vault / 'proposals' / 'pending' / 'p2.json', _proposal('p2'))
    subprocess.run(
        [sys.executable, '-m', 'eva.repair.cli', 'reject', 'p1', '--vault', str(vault), '--note', 'no'],
        check=True,
    )
    subprocess.run(
        [sys.executable, '-m', 'eva.repair.cli', 'defer', 'p2', '--vault', str(vault), '--note', 'later'],
        check=True,
    )
    assert (vault / 'proposals' / 'rejected' / 'p1.json').exists()
    assert (vault / 'proposals' / 'deferred' / 'p2.json').exists()


def test_eva_repair_cli_list_rejects_invalid_state(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    result = subprocess.run(
        [sys.executable, '-m', 'eva.repair.cli', 'list', '--vault', str(vault), '--state', 'pendingg'],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert 'invalid proposal state' in result.stderr


def test_eva_repair_cli_ambiguous_prefix_does_not_move_wrong_proposal(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(vault / 'proposals' / 'pending' / 'p10.json', _proposal('p10'))
    atomic_write_json(vault / 'proposals' / 'pending' / 'p11.json', _proposal('p11'))
    result = subprocess.run(
        [sys.executable, '-m', 'eva.repair.cli', 'approve', 'p1', '--vault', str(vault), '--note', 'ambiguous'],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert 'ambiguous proposal id prefix' in result.stderr
    assert not list((vault / 'proposals' / 'approved').glob('*.json'))
    assert (vault / 'proposals' / 'pending' / 'p10.json').exists()
    assert (vault / 'proposals' / 'pending' / 'p11.json').exists()


def test_eva_repair_draft_all_defaults_to_pending_only(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(vault / 'proposals' / 'pending' / 'p1.json', _proposal('p1'))
    atomic_write_json(vault / 'proposals' / 'approved' / 'p2.json', {**_proposal('p2'), 'status': 'approved'})
    result = subprocess.run(
        [sys.executable, '-m', 'eva.repair.cli', 'draft-all', '--vault', str(vault), '--write', '--json'],
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(result.stdout)
    assert data['count'] == 1
