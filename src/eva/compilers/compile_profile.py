"""EVA operator-profile compiler."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from eva.common import (
    EVA_VAULT_DIR,
    atomic_write_json,
    atomic_write_text,
    ensure_vault,
    read_json,
    safe_snippet,
    utc_now,
)
from eva.settings import load_settings

PREFERENCE_HINTS = {
    "communication_style": ["concise", "terminal-readable", "telegram", "markdown", "tables"],
    "execution_style": ["autonomous", "verification", "smoke test", "proceed optimally", "tool"],
    "github_conventions": ["github", "public", "private", "lab", "repo", "noreply"],
    "routing_rules": ["deepseek", "codex", "gemini", "swarm", "delegate", "profile"],
    "project_lifecycle": ["dead", "shelved", "phased out", "active", "eva", "antaeus"],
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def _latest_scan(vault: Path) -> dict[str, Any]:
    path = vault / "briefs" / "latest-scan.json"
    return read_json(path) if path.exists() else {}


def _extract_preferences(memory_scan: dict[str, Any], corrections: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    prefs: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    entries = []
    for md in memory_scan.get("memory_data", []):
        for entry in md.get("entries", []):
            entries.append({"source": f"memory:{md.get('profile')}:{md.get('target')}:{entry.get('index')}", "text": entry.get("text", "")})
    for correction in corrections[-100:]:
        entries.append({"source": f"session:{correction.get('profile')}:{correction.get('session_id')}", "text": correction.get("text", "")})

    for item in entries:
        text_l = item["text"].lower()
        for category, keywords in PREFERENCE_HINTS.items():
            if any(k in text_l for k in keywords):
                prefs[category].append({"source": item["source"], "evidence": safe_snippet(item["text"], 180)})
    return {k: v[:25] for k, v in prefs.items()}


def compile_profile(scan_bundle: dict[str, Any] | None = None, vault: str | Path = EVA_VAULT_DIR, write: bool = True) -> dict[str, Any]:
    vault = ensure_vault(Path(vault)) if write else Path(vault).expanduser()
    bundle = scan_bundle or _latest_scan(vault)
    corrections = _load_jsonl(vault / "evidence" / "corrections.jsonl")
    failures = _load_jsonl(vault / "evidence" / "failures.jsonl")
    memory_scan = bundle.get("memory", bundle if bundle.get("scanner") == "memory" else {})
    sessions = bundle.get("sessions", {})
    skills = bundle.get("skills", {})
    configs = bundle.get("configs", {})

    top_failure_tools = Counter(f.get("tool", "unknown") for f in failures).most_common(10)
    preferences = _extract_preferences(memory_scan, corrections + sessions.get("corrections", []))

    settings = load_settings(vault)
    operator_name = str(settings.get("operator", {}).get("name") or "Operator")

    profile = {
        "generated_at": utc_now(),
        "schema_version": "0.1",
        "operator": operator_name,
        "confidence": "evidence-derived draft; operator approval required for durable memory changes",
        "preferences": preferences,
        "system_health": {
            "memory": memory_scan.get("summary", {}),
            "sessions": sessions.get("summary", {}),
            "skills": skills.get("summary", {}),
            "configs": configs.get("summary", {}),
            "top_failure_tools": [{"tool": t, "count": c} for t, c in top_failure_tools],
        },
        "routing_observations": configs.get("model_matrix", [])[:50],
        "proposal_inputs": {
            "contradictions": memory_scan.get("contradictions", [])[:25],
            "orphan_references": memory_scan.get("orphan_references", [])[:25],
            "repeated_failures": sessions.get("repeated_failures", [])[:25],
            "oversized_skills": skills.get("oversized_skills", [])[:25],
            "config_drift": configs.get("drift", [])[:25],
        },
    }
    if write:
        atomic_write_json(vault / "context" / "operator-profile.json", profile)
        atomic_write_text(vault / "context" / "operator-profile.md", render_profile_markdown(profile))
    return profile


def render_profile_markdown(profile: dict[str, Any]) -> str:
    lines = ["# EVA Operator Profile", "", f"Generated: {profile.get('generated_at')}", "", f"Confidence: {profile.get('confidence')}", ""]
    lines.append("## Preferences")
    prefs = profile.get("preferences", {})
    if not prefs:
        lines.append("- No evidence-backed preferences extracted yet.")
    for category, items in prefs.items():
        lines.append(f"### {category.replace('_', ' ').title()}")
        for item in items[:10]:
            lines.append(f"- {item['evidence']}  ")
            lines.append(f"  Source: `{item['source']}`")
    lines.append("")
    lines.append("## Health Snapshot")
    health = profile.get("system_health", {})
    for key, value in health.items():
        lines.append(f"- **{key}**: `{json.dumps(value)[:500]}`")
    lines.append("")
    lines.append("## Proposal Inputs")
    for key, value in profile.get("proposal_inputs", {}).items():
        lines.append(f"- **{key}**: {len(value)} item(s)")
    lines.append("")
    lines.append("Operator note: EVA proposes changes only; it does not auto-apply them.")
    return "\n".join(lines)


def main() -> None:
    scan_bundle = None
    if len(sys.argv) > 1:
        scan_bundle = read_json(Path(sys.argv[1]))
    profile = compile_profile(scan_bundle)
    print(json.dumps(profile, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
