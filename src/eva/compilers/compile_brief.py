"""
EVA brief compiler — reads scan output JSON and produces a human-readable
operator brief designed for Stefan's Telegram home channel.

Input: scan output JSON (from scan_memory.py, etc.)
Output: markdown brief text
"""

from __future__ import annotations

import json
import sys
from typing import Any


def compile_brief(scan_results: dict[str, Any]) -> str:
    """Compile scan results into a human-readable operator brief."""

    lines = [
        "## EVA Scan",
        "",
        f"**Scanner:** {scan_results.get('scanner', 'unknown')}",
        f"**Timestamp:** {scan_results.get('timestamp', '?')[:19]}",
    ]

    summary = scan_results.get("summary", {})
    if summary:
        lines.append("")
        lines.append(f"Scanned {summary.get('files_scanned', '?')} files across {len(summary.get('profiles', []))} profiles — {summary.get('total_entries', '?')} total entries.")

    # ── Key findings ────────────────────────────────────────────────────
    lines.append("")
    lines.append("### Findings")

    contradictions = scan_results.get("contradictions", [])
    orphans = scan_results.get("orphan_references", [])
    duplicates = scan_results.get("duplicates", [])

    if not contradictions and not orphans and not duplicates:
        lines.append("No issues found. System memory looks clean.")
    else:
        if contradictions:
            lines.append(f"**{len(contradictions)} potential contradictions**")
            # Deduplicate by reason
            reasons = {}
            for c in contradictions:
                reason = c.get("reason", "Unknown")
                if reason not in reasons:
                    reasons[reason] = []
                reasons[reason].append(c)
            for reason, items in reasons.items():
                profiles_involved = {c["entry_a"]["profile"] for c in items}
                lines.append(f"- *{reason}* — found in {', '.join(sorted(profiles_involved))} ({len(items)} pair{'s' if len(items) > 1 else ''})")
            lines.append("")

        if orphans:
            # Filter out duplicates by text
            seen = set()
            unique_orphans = []
            for o in orphans:
                key = (o["profile"], o["keyword"])
                if key not in seen:
                    seen.add(key)
                    unique_orphans.append(o)

            lines.append(f"**{len(unique_orphans)} distinct orphan references found**")
            by_keyword = {}
            for o in unique_orphans:
                kw = o["keyword"]
                if kw not in by_keyword:
                    by_keyword[kw] = []
                by_keyword[kw].append(o["profile"])
            for kw, profiles in sorted(by_keyword.items()):
                lines.append(f"- `{kw}` referenced in {', '.join(sorted(set(profiles)))}")
            lines.append("")

        if duplicates:
            lines.append(f"**{len(duplicates)} near-duplicate entries** (>85% similarity)")

    # ── Topics ──────────────────────────────────────────────────────────
    topics = scan_results.get("topics", {})
    if topics:
        lines.append("")
        lines.append("### Topic Distribution")
        for topic, count in list(topics.items())[:10]:
            bar = "█" * min(count, 30)
            lines.append(f"- **{topic}**: {count} entries {bar}")
        lines.append("")

    # ── Health ──────────────────────────────────────────────────────────
    health = scan_results.get("health", {})
    if health:
        lines.append("")
        lines.append("### Scanner Health")
        for key, val in health.items():
            lines.append(f"- **{key}**: {val}")
        lines.append("")

    # ── Footer ──────────────────────────────────────────────────────────
    lines.append("---")
    lines.append("*EVA — Evidence & Verification Agent*")

    return "\n".join(lines)


def main():
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    print(compile_brief(data))


if __name__ == "__main__":
    main()
