"""Compile EVA scan outputs into a operator-readable brief."""

from __future__ import annotations

import json
import sys
from typing import Any


def _count(scan: dict[str, Any], key: str, default: int = 0) -> int:
    value = scan.get("summary", {}).get(key, default)
    return int(value or 0)


def _section_memory(scan: dict[str, Any]) -> list[str]:
    lines = ["### Memory"]
    summary = scan.get("summary", {})
    lines.append(
        f"Scanned {summary.get('files_scanned', '?')} files across {len(summary.get('profiles', []))} profiles — {summary.get('total_entries', '?')} entries."
    )
    contradictions = scan.get("contradictions", [])
    orphans = scan.get("orphan_references", [])
    duplicates = scan.get("duplicates", [])
    if not contradictions and not orphans and not duplicates:
        lines.append("- No memory issues found.")
    else:
        if contradictions:
            reasons: dict[str, int] = {}
            for item in contradictions:
                reasons[item.get("reason", "unknown")] = reasons.get(item.get("reason", "unknown"), 0) + 1
            lines.append(f"- **{len(contradictions)} potential contradictions**")
            for reason, count in sorted(reasons.items()):
                lines.append(f"  - {reason}: {count}")
        if orphans:
            by_keyword: dict[str, set[str]] = {}
            for item in orphans:
                by_keyword.setdefault(item.get("keyword", "unknown"), set()).add(item.get("profile", "?"))
            lines.append(f"- **{len(orphans)} orphan/stale references**")
            for keyword, profiles in sorted(by_keyword.items()):
                lines.append(f"  - `{keyword}`: {', '.join(sorted(profiles))}")
        if duplicates:
            lines.append(f"- **{len(duplicates)} near-duplicate entries**")
    return lines


def _section_sessions(scan: dict[str, Any]) -> list[str]:
    lines = ["### Sessions"]
    summary = scan.get("summary", {})
    lines.append(
        f"Scanned {summary.get('messages_scanned', 0)} messages across {summary.get('profiles_scanned', 0)} profiles ({summary.get('window_days', '?')}d window)."
    )
    lines.append(f"- Corrections: {summary.get('corrections_found', 0)}")
    lines.append(f"- Tool failures: {summary.get('tool_failures_found', 0)}")
    lines.append(f"- Skill patches: {summary.get('skill_patches_found', 0)}")
    repeated = scan.get("repeated_failures", [])
    if repeated:
        lines.append("- Repeated failure tools:")
        for item in repeated[:8]:
            lines.append(f"  - `{item.get('tool')}`: {item.get('count')}")
    return lines


def _section_skills(scan: dict[str, Any]) -> list[str]:
    lines = ["### Skills"]
    summary = scan.get("summary", {})
    lines.append(f"Scanned {summary.get('skills_scanned', 0)} skills across {summary.get('profiles_scanned', 0)} profiles.")
    lines.append(f"- Oversized: {summary.get('oversized_count', 0)}")
    lines.append(f"- Stale candidates: {summary.get('stale_count', 0)}")
    lines.append(f"- Duplicate names across profiles: {summary.get('duplicate_name_count', 0)}")
    oversized = scan.get("oversized_skills", [])
    if oversized:
        lines.append("- Oversized examples:")
        for item in oversized[:5]:
            lines.append(f"  - `{item.get('name')}` ({item.get('profile')}, {item.get('size_bytes')} bytes)")
    return lines


def _section_configs(scan: dict[str, Any]) -> list[str]:
    lines = ["### Config Drift"]
    summary = scan.get("summary", {})
    lines.append(f"Scanned {summary.get('profiles_scanned', 0)} profiles; drift findings: {summary.get('drift_findings', 0)}.")
    drift = scan.get("drift", [])
    for item in drift[:10]:
        lines.append(f"- `{item.get('role_group')}` drift on `{item.get('key')}`")
    return lines


def _section_memory_provider(scan: dict[str, Any]) -> list[str]:
    lines = ["### Memory Provider"]
    summary = scan.get("summary", {})
    lines.append(f"Cell: `{summary.get('cell')}` — exists: {summary.get('exists')}")
    lines.append(
        f"- Charges: {summary.get('approved_charges', 0)} approved, "
        f"{summary.get('deprecated_charges', 0)} deprecated, {summary.get('isolated_charges', 0)} isolated"
    )
    lines.append(
        f"- Ledgers: {summary.get('sources', 0)} sources, {summary.get('fragments', 0)} fragments, "
        f"{summary.get('diagnostics', 0)} diagnostics"
    )
    profiles = summary.get("configured_profiles", [])
    if profiles:
        lines.append(f"- Hermes profiles configured for this memory provider: {', '.join(profiles)}")
    modes = summary.get("profile_modes") or {}
    if modes:
        lines.append("- Authority modes: " + ", ".join(f"{name}={mode}" for name, mode in sorted(modes.items())))
    operations = summary.get("diagnostic_operations", {})
    if operations:
        lines.append("- Diagnostic operations:")
        for op, count in sorted(operations.items()):
            lines.append(f"  - `{op}`: {count}")
    return lines


def _section_profile(scan: dict[str, Any]) -> list[str]:
    prefs = scan.get("preferences", {})
    lines = ["### Operator Profile"]
    if prefs:
        lines.append(f"Generated with {len(prefs)} evidence-backed preference categories.")
        for key, items in prefs.items():
            lines.append(f"- **{key.replace('_', ' ')}**: {len(items)} evidence item(s)")
    else:
        lines.append("No operator-profile preferences extracted yet.")
    return lines


def _section_proposals(scan: dict[str, Any]) -> list[str]:
    lines = ["### Proposals"]
    proposals = scan.get("proposals", [])
    if not proposals:
        lines.append("No pending proposal drafts generated.")
    else:
        lines.append(f"Generated {len(proposals)} pending proposal draft(s):")
        for p in proposals[:10]:
            lines.append(f"- `{p.get('kind')}` — {p.get('title')}")
    return lines


def compile_brief(scan_results: dict[str, Any]) -> str:
    """Compile a single scan or combined scan bundle into a human-readable brief."""
    scanner = scan_results.get("scanner", "combined")
    timestamp = scan_results.get("timestamp", scan_results.get("generated_at", "?"))
    lines = ["## EVA Scan", "", f"**Scanner:** {scanner}", f"**Timestamp:** {str(timestamp)[:19]}", ""]

    if scanner == "combined":
        sections = [
            ("memory", _section_memory),
            ("sessions", _section_sessions),
            ("skills", _section_skills),
            ("configs", _section_configs),
            ("memory_provider", _section_memory_provider),
            ("operator_profile", _section_profile),
            ("proposal_summary", _section_proposals),
        ]
        for key, renderer in sections:
            if key in scan_results:
                lines.extend(renderer(scan_results[key]))
                lines.append("")
    elif scanner == "memory":
        lines.extend(_section_memory(scan_results))
    elif scanner == "sessions":
        lines.extend(_section_sessions(scan_results))
    elif scanner == "skills":
        lines.extend(_section_skills(scan_results))
    elif scanner == "configs":
        lines.extend(_section_configs(scan_results))
    elif scanner == "memory_provider":
        lines.extend(_section_memory_provider(scan_results))
    else:
        summary = scan_results.get("summary", {})
        lines.append(f"Summary: `{json.dumps(summary)[:800]}`")

    health_lines: list[str] = []
    for key, value in scan_results.items():
        if isinstance(value, dict) and value.get("health"):
            degraded = value["health"].get("degraded_profiles")
            if degraded:
                health_lines.append(f"- {key}: degraded profiles: {len(degraded)}")
    if health_lines:
        lines.append("### Scanner Health")
        lines.extend(health_lines)
        lines.append("")

    lines.append("---")
    lines.append("*EVA — Evidence & Verification Agent. Proposals only; no auto-apply.*")
    return "\n".join(lines).strip() + "\n"


def main() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)
    print(compile_brief(data), end="")


if __name__ == "__main__":
    main()
