"""EVA memory-provider scanner — records local memory cell and diagnostic-log health."""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eva.common import HERMES_PROFILES_DIR

DEFAULT_CELL = Path(
    os.environ.get(
        "EVA_MEMORY_CELL",
        Path.home() / ".hermes" / "memory" / "cells" / "default",
    )
).expanduser()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
        except json.JSONDecodeError:
            rows.append({"_parse_error": line[:240]})
    return rows


def _ledger_counts(cell: Path) -> dict[str, int]:
    ledger = cell / "ledger"
    charges = cell / "charges"
    return {
        "sources": len(_read_jsonl(ledger / "sources.jsonl")),
        "fragments": len(_read_jsonl(ledger / "fragments.jsonl")),
        "diagnostics": len(_read_jsonl(ledger / "diagnostic_logs.jsonl")),
        "approved_charges": len(_read_jsonl(charges / "approved.jsonl")) + len(_read_jsonl(cell / "traces" / "approved.jsonl")),
        "deprecated_charges": len(_read_jsonl(charges / "deprecated.jsonl")) + len(_read_jsonl(cell / "traces" / "deprecated.jsonl")),
        "isolated_charges": len(_read_jsonl(charges / "isolated.jsonl")) + len(_read_jsonl(cell / "traces" / "isolated.jsonl")),
    }


def run_scan(cell: str | Path = DEFAULT_CELL, vault: str | Path | None = None) -> dict[str, Any]:
    cell_path = Path(cell).expanduser()
    diagnostics = _read_jsonl(cell_path / "ledger" / "diagnostic_logs.jsonl")
    by_operation = Counter(str(row.get("operation") or "unknown") for row in diagnostics)
    statuses = Counter(str(row.get("status") or "unknown") for row in diagnostics)
    recent = diagnostics[-10:]
    manifest_path = cell_path / "config" / "cell_manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {"parse_error": str(manifest_path)}
    configured_profiles: list[str] = []
    profile_modes: dict[str, str] = {}
    runtime_primary_profiles: list[str] = []
    bounded_primary_profiles: list[str] = []
    profiles_dir = HERMES_PROFILES_DIR
    if profiles_dir.exists():
        for cfg in profiles_dir.glob("*/memory-provider.json"):
            try:
                data = json.loads(cfg.read_text(encoding="utf-8"))
                if Path(str(data.get("cell_path", ""))).expanduser() == cell_path:
                    configured_profiles.append(cfg.parent.name)
                    mode = str(data.get("mode") or "advisory").replace("-", "_")
                    profile_modes[cfg.parent.name] = mode
                    if mode == "runtime_primary":
                        runtime_primary_profiles.append(cfg.parent.name)
                    elif mode == "bounded_primary":
                        bounded_primary_profiles.append(cfg.parent.name)
            except Exception:
                continue
    summary = {
        "cell": str(cell_path),
        "exists": cell_path.exists(),
        "cell_id": manifest.get("cell_id", cell_path.name),
        "configured_profiles": sorted(configured_profiles),
        "profile_modes": dict(sorted(profile_modes.items())),
        "bounded_primary_profiles": sorted(bounded_primary_profiles),
        "runtime_primary_profiles": sorted(runtime_primary_profiles),
        **_ledger_counts(cell_path),
        "diagnostic_operations": dict(sorted(by_operation.items())),
        "diagnostic_statuses": dict(sorted(statuses.items())),
    }
    return {
        "scanner": "memory_provider",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "recent_diagnostics": recent,
        "health": {
            "canonical_truth": "Memory-provider append-only ledgers",
            "diagnostics_role": "diagnostics explain decisions; they are not canonical memory truth",
            "replacement_boundary": "advisory/bounded pilot only unless operator approves expansion",
        },
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Scan memory-provider diagnostics for EVA")
    parser.add_argument("--cell", default=str(DEFAULT_CELL))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_scan(args.cell)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
