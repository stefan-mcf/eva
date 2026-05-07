"""Repair artifact IO helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from eva.common import atomic_write_json, ensure_vault, read_json
from eva.proposals import PROPOSAL_STATES
from eva.repair.schemas import validate_repair_bundle

REPAIR_BUNDLE_STATES = ("drafts", "approved", "applied", "failed")
DEFAULT_PROPOSAL_LIST_STATES = ["pending"]


def _validate_proposal_states(states: list[str]) -> None:
    invalid = sorted(set(states) - PROPOSAL_STATES)
    if invalid:
        raise ValueError(f"invalid proposal state(s): {', '.join(invalid)}")


def write_repair_bundle(bundle: dict[str, Any], vault: str | Path) -> Path:
    errors = validate_repair_bundle(bundle)
    if errors:
        raise ValueError("invalid repair bundle: " + "; ".join(errors))
    vault_path = ensure_vault(Path(vault).expanduser())
    status_dir = "approved" if bundle.get("status") == "approved" else "drafts"
    path = vault_path / "repairs" / status_dir / f"{bundle['id']}.json"
    atomic_write_json(path, bundle)
    return path


def load_repair_bundle(bundle_id: str, vault: str | Path) -> tuple[Path, dict[str, Any]]:
    vault_path = Path(vault).expanduser()
    exact_matches: list[tuple[Path, dict[str, Any]]] = []
    prefix_matches: list[tuple[Path, dict[str, Any]]] = []
    for state in REPAIR_BUNDLE_STATES:
        for path in sorted((vault_path / "repairs" / state).glob("*.json")):
            data = read_json(path)
            if data.get("id") == bundle_id or path.stem == bundle_id:
                exact_matches.append((path, data))
            elif str(data.get("id", "")).startswith(bundle_id) or path.stem.startswith(bundle_id):
                prefix_matches.append((path, data))
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise ValueError(f"ambiguous repair bundle id: {bundle_id}")
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if len(prefix_matches) > 1:
        raise ValueError(f"ambiguous repair bundle id prefix: {bundle_id}")
    raise FileNotFoundError(f"repair bundle not found: {bundle_id}")


def list_proposals(vault: str | Path, states: list[str] | None = None) -> list[dict[str, Any]]:
    vault_path = Path(vault).expanduser()
    selected_states = states or DEFAULT_PROPOSAL_LIST_STATES
    _validate_proposal_states(selected_states)
    proposals = []
    for state in selected_states:
        for path in sorted((vault_path / "proposals" / state).glob("*.json")):
            data = read_json(path)
            data["_path"] = str(path)
            proposals.append(data)
    return proposals
