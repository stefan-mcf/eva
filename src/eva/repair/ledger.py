"""Operator repair ledger."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from eva.common import atomic_write_json, atomic_write_text, utc_now
from eva.repair.drafters import is_hardening_candidate
from eva.repair.schemas import REPAIR_LEDGER_SCHEMA

OPERATOR_ACTIONS = ["approve", "reject", "defer", "amend", "escalate_to_repair_intake", "accept_warn", "block_intentionally", "supersede", "close_resolved_by_later_proof"]


def compile_repair_ledger(bundles: list[dict[str, Any]], *, source_scan_timestamp: str | None = None) -> dict[str, Any]:
    items = []
    for bundle in bundles:
        proposal = {"kind": bundle.get("source_proposal_kind")}
        items.append({
            "repair_bundle_id": bundle.get("id"),
            "proposal_id": bundle.get("source_proposal_id"),
            "proposal_kind": bundle.get("source_proposal_kind"),
            "risk": bundle.get("risk"),
            "target_class": bundle.get("target_class"),
            "approval_state": bundle.get("operator_decision", {}).get("state"),
            "auto_apply_allowed": bundle.get("auto_apply_allowed", False),
            "affected_paths": bundle.get("affected_paths", []),
            "planned_action_types": [a.get("action_type") for a in bundle.get("planned_actions", [])],
            "verification": bundle.get("verification", []),
            "hardening_candidate": is_hardening_candidate(proposal),
            "hardening_reason": "Recurring evidence may deserve durable hardening" if is_hardening_candidate(proposal) else "",
        })
    return {"schema": REPAIR_LEDGER_SCHEMA, "generated_at": utc_now(), "source_scan_timestamp": source_scan_timestamp, "summary": {"bundle_count": len(bundles), "human_gated_count": sum(1 for b in bundles if b.get("requires_human_gate")), "auto_safe_count": sum(1 for b in bundles if b.get("auto_apply_allowed"))}, "items": items, "operator_actions": OPERATOR_ACTIONS}


def render_repair_ledger_markdown(ledger: dict[str, Any]) -> str:
    lines = ["# EVA Repair Ledger", "", f"Generated: `{ledger.get('generated_at','')}`", f"Source scan: `{ledger.get('source_scan_timestamp','')}`", "", "## Items"]
    for item in ledger.get("items", []):
        lines.append(f"- `{item.get('repair_bundle_id')}` proposal=`{item.get('proposal_id')}` kind=`{item.get('proposal_kind')}` risk=`{item.get('risk')}` target=`{item.get('target_class')}` auto_apply=`{str(item.get('auto_apply_allowed')).lower()}` approval=`{item.get('approval_state')}`")
    lines.extend(["", "## Operator Actions"])
    for action in ledger.get("operator_actions", []):
        lines.append(f"- `{action}`")
    lines.append("")
    return "\n".join(lines)


def write_repair_ledger(ledger: dict[str, Any], vault: str | Path, stamp: str | None = None) -> dict[str, str]:
    vault_path = Path(vault).expanduser()
    stamp = stamp or utc_now().replace(":", "").replace("+", "Z")
    paths = {"latest_json": vault_path / "repairs" / "ledger" / "latest-ledger.json", "latest_markdown": vault_path / "repairs" / "ledger" / "latest-ledger.md", "timestamped_json": vault_path / "repairs" / "ledger" / f"ledger-{stamp}.json", "timestamped_markdown": vault_path / "repairs" / "ledger" / f"ledger-{stamp}.md"}
    markdown = render_repair_ledger_markdown(ledger)
    atomic_write_json(paths["latest_json"], ledger)
    atomic_write_text(paths["latest_markdown"], markdown)
    atomic_write_json(paths["timestamped_json"], ledger)
    atomic_write_text(paths["timestamped_markdown"], markdown)
    return {k: str(v) for k, v in paths.items()}
