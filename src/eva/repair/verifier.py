"""Verification helpers for EVA repair outcomes."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def verify_repair_outcome(outcome: dict[str, Any], *, vault: str | Path) -> dict[str, Any]:
    vault_path = Path(vault).expanduser()
    checks = []
    for action in outcome.get("actions_succeeded", []):
        rel = action.get("path")
        if rel:
            p = vault_path / rel
            checks.append({"name": f"exists:{rel}", "ok": p.exists()})
    ok = all(c["ok"] for c in checks) if checks else outcome.get("status") in {"blocked", "failed"}
    return {"status": "ok" if ok else "failed", "checks": checks, "outcome_status": outcome.get("status")}
