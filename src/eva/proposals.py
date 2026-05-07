"""Proposal lifecycle helpers for EVA."""
from __future__ import annotations

from typing import Any

PROPOSAL_STATES = {"pending", "approved", "rejected", "deferred", "applied", "superseded"}
TERMINAL_PROPOSAL_STATES = {"rejected", "applied", "superseded"}
ACTIVE_PROPOSAL_STATES = {"pending", "approved", "deferred"}


def normalize_proposal_state(value: str) -> str:
    state = str(value or "").strip().lower()
    if state not in PROPOSAL_STATES:
        raise ValueError(f"unknown proposal state: {value}")
    return state


def proposal_dedupe_key(proposal: dict[str, Any]) -> str:
    metadata = proposal.get("metadata") if isinstance(proposal.get("metadata"), dict) else {}
    if metadata.get("dedupe_key"):
        return str(metadata["dedupe_key"])
    return f"{proposal.get('kind', 'unknown')}:{proposal.get('title', '')}"
