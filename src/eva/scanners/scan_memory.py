"""
EVA memory scanner — reads the Hermes memory DB and flags contradictions, staleness, and orphaned entries.

Hermes memory is stored as SQLite at ~/.hermes/memory.db (or profile-local equivalent).
Schema (as of May 2026): entries table with id, content, target, created_at, updated_at.

This scanner is read-only. It never writes to memory.
"""

from __future__ import annotations

import sqlite3
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ─── Configuration ──────────────────────────────────────────────────────────

STALENESS_DAYS = 90  # entries older than this without updates are flagged
CONTRADICTION_SIMILARITY = 0.7  # placeholder threshold (unused in v0)


def resolve_memory_db(hermes_home: str | None = None) -> Path:
    """Find the Hermes memory DB, checking profile-local then global."""
    candidate = Path(hermes_home or os.path.expanduser("~/.hermes")) / "memory.db"
    if candidate.exists():
        return candidate
    global_candidate = Path(os.path.expanduser("~/.hermes")) / "memory.db"
    if global_candidate.exists():
        return global_candidate
    raise FileNotFoundError("Could not locate Hermes memory.db")


def load_entries(db_path: Path) -> list[dict[str, Any]]:
    """Load all memory entries as dicts."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT id, content, target, created_at, updated_at FROM entries ORDER BY updated_at DESC"
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


# ─── Scanners ────────────────────────────────────────────────────────────────

def find_contradictions(entries: list[dict]) -> list[dict]:
    """
    Find entries that semantically contradict each other.
    v0: simple keyword overlap heuristic. Future: embedding-based.
    Returns list of {entry_a_id, entry_b_id, overlap, reason}.
    """
    findings = []
    # Placeholder — semantic contradiction detection needs embeddings
    # For v0 we return empty and note the limitation in the brief.
    return findings


def find_stale_entries(entries: list[dict]) -> list[dict]:
    """Find entries that haven't been updated in STALENESS_DAYS."""
    now = datetime.now(timezone.utc)
    stale = []
    for entry in entries:
        updated = entry.get("updated_at")
        if not updated:
            continue
        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        if (now - dt).days > STALENESS_DAYS:
            stale.append({"id": entry["id"], "days_old": (now - dt).days, "target": entry["target"]})
    return stale


def find_orphan_entries(entries: list[dict]) -> list[dict]:
    """Find entries that reference tools/skills/profiles that no longer exist."""
    # Placeholder for v0 — needs filesystem scan for skill/profile existence.
    return []


# ─── Main scan ───────────────────────────────────────────────────────────────

def run_scan(hermes_home: str | None = None) -> dict:
    """Run all memory scanners and return structured findings."""
    db_path = resolve_memory_db(hermes_home)
    entries = load_entries(db_path)

    contradictions = find_contradictions(entries)
    stale = find_stale_entries(entries)
    orphans = find_orphan_entries(entries)

    return {
        "scanner": "memory",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(entries),
        "findings": {
            "contradictions": contradictions,
            "stale": stale,
            "orphans": orphans,
        },
        "health": {
            "contradiction_scanner": "STUB — keyword-only, no semantic detection",
            "orphan_scanner": "STUB — needs skills/profile filesystem scan",
        },
    }


if __name__ == "__main__":
    import sys

    hermes_home = sys.argv[1] if len(sys.argv) > 1 else None
    result = run_scan(hermes_home)
    print(json.dumps(result, indent=2))
