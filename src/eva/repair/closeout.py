"""Closeout reports for EVA repairs."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from eva.common import atomic_write_json, atomic_write_text, read_json, utc_now


def compile_closeout_report(
    vault: str | Path,
    *,
    before_scan: dict[str, Any] | None = None,
    after_scan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    vault_path = Path(vault).expanduser()
    applied = list((vault_path / "repairs" / "applied").glob("*outcome.json"))
    failed = list((vault_path / "repairs" / "failed").glob("*outcome.json"))
    drafts = list((vault_path / "repairs" / "drafts").glob("*.json"))
    human_gated = 0
    for path in drafts:
        try:
            if read_json(path).get("requires_human_gate"):
                human_gated += 1
        except Exception:
            continue
    return {
        "schema": "eva-repair-closeout/v1",
        "generated_at": utc_now(),
        "summary": {
            "draft_bundles": len(drafts),
            "applied_outcomes": len(applied),
            "failed_or_blocked_outcomes": len(failed),
            "unresolved_human_gated": human_gated,
        },
        "artifacts": {"vault": str(vault_path)},
        "before_scan_timestamp": (before_scan or {}).get("timestamp"),
        "after_scan_timestamp": (after_scan or {}).get("timestamp"),
    }


def render_closeout_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    return "\n".join(
        [
            "# EVA Repair Closeout",
            "",
            f"Generated: `{report.get('generated_at', '')}`",
            "",
            "## Summary",
            f"- Draft bundles: {summary.get('draft_bundles', 0)}",
            f"- Applied outcomes: {summary.get('applied_outcomes', 0)}",
            f"- Failed/blocked outcomes: {summary.get('failed_or_blocked_outcomes', 0)}",
            f"- Unresolved human-gated: {summary.get('unresolved_human_gated', 0)}",
            "",
        ]
    )


def write_closeout_report(
    report: dict[str, Any],
    vault: str | Path,
    stamp: str | None = None,
) -> dict[str, str]:
    vault_path = Path(vault).expanduser()
    stamp = stamp or utc_now().replace(":", "").replace("+", "Z")
    md = render_closeout_markdown(report)
    paths = {
        "latest_json": vault_path / "repairs" / "ledger" / "latest-closeout.json",
        "latest_markdown": vault_path / "repairs" / "ledger" / "latest-closeout.md",
        "timestamped_json": vault_path / "repairs" / "ledger" / f"closeout-{stamp}.json",
        "timestamped_markdown": vault_path / "repairs" / "ledger" / f"closeout-{stamp}.md",
    }
    atomic_write_json(paths["latest_json"], report)
    atomic_write_text(paths["latest_markdown"], md)
    atomic_write_json(paths["timestamped_json"], report)
    atomic_write_text(paths["timestamped_markdown"], md)
    return {key: str(value) for key, value in paths.items()}
