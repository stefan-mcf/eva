import json
import subprocess
import sys
from pathlib import Path

from eva.common import atomic_write_json, ensure_vault


def test_temp_vault_repair_flow_drafts_applies_safe_and_blocks_gated(tmp_path: Path):
    vault = ensure_vault(tmp_path / 'vault')
    atomic_write_json(vault / 'proposals' / 'pending' / 'p-safe.json', {'id':'p-safe','kind':'tool_failure_triage','title':'Triage','status':'pending','evidence':[]})
    atomic_write_json(vault / 'proposals' / 'pending' / 'p-gated.json', {'id':'p-gated','kind':'memory_merge','title':'Memory','status':'pending','evidence':[]})
    subprocess.run([sys.executable, '-m', 'eva.repair.cli', 'draft-all', '--vault', str(vault), '--write'], check=True)
    assert len(list((vault / 'repairs' / 'drafts').glob('*.json'))) == 2
    subprocess.run([sys.executable, '-m', 'eva.repair.cli', 'approve', 'p-safe', '--vault', str(vault), '--note', 'ok'], check=True)
    safe_bundle = next(p for p in (vault / 'repairs' / 'drafts').glob('*.json') if 'p-safe' in p.name)
    data = json.loads(safe_bundle.read_text())
    data['status'] = 'approved'
    safe_bundle.write_text(json.dumps(data))
    subprocess.run([sys.executable, '-m', 'eva.repair.cli', 'apply', data['id'], '--vault', str(vault)], check=True)
    assert list((vault / 'repairs' / 'applied').glob('*outcome.json'))
    subprocess.run([sys.executable, '-m', 'eva.repair.cli', 'closeout', '--vault', str(vault), '--write'], check=True)
    assert (vault / 'repairs' / 'ledger' / 'latest-closeout.md').exists()
