"""
EVA memory scanner — reads Hermes markdown-format memory files and flags
contradictions, staleness, orphan references, and structural issues.

Hermes memory (as of May 2026) is stored as:
  ~/.hermes/profiles/<profile>/memories/MEMORY.md   (agent notes)
  ~/.hermes/profiles/<profile>/memories/USER.md     (user profile)

Format: Section header with percentage + capacity, entries separated by '§'.
Each entry is a free-text paragraph/sentence. No SQLite.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eva.common import HERMES_PROFILES_DIR
from eva.settings import load_settings

# ─── Configuration ──────────────────────────────────────────────────────────

STALENESS_DAYS = 90  # Entries that haven't changed in this many days are flagged
CONTRADICTION_KEYWORDS = {
    # Pairs of keywords that suggest contradictory entries
    ("always", "never"): "Direct contradiction",
    ("public", "private"): "Visibility contradiction",
    ("ssh", "do not ssh"): "SSH access contradiction",
    ("antaeus", "dead"): "Project lifecycle contradiction",
    ("lab", "no lab"): "Naming convention contradiction",
}
ORPHAN_KEYWORDS = [
    # Known dead/stale project names
    "antaeus",
    "antaeus-terminal",
    "antaeus-terminal-side",
    "courier",
    "shyftr",
]

PROFILES_GLOB = str(HERMES_PROFILES_DIR)


# ─── Memory file parsing ────────────────────────────────────────────────────

def parse_memory_file(path: Path) -> dict[str, Any]:
    """
    Parse a Hermes MEMORY.md or USER.md file.
    Returns: {file, target, total_entries, entries: [{index, text, keywords}]}
    """
    with open(path) as f:
        content = f.read()

    target = "memory" if "MEMORY" in path.name else "user"
    entries = []
    # Header format: "═══════════════\nMEMORY (your personal notes) [76% — 1,691/2,200 chars]\n..."
    # Strip header lines until first § or paragraph content
    lines = content.split("\n")
    in_header = True
    buffer = []

    for line in lines:
        # Skip decorative lines and header info
        if in_header:
            if line.strip().startswith("═══"):
                continue
            if line.strip().startswith("MEMORY") or line.strip().startswith("USER"):
                continue
            if "chars]" in line or "chars)" in line:
                continue
            if not line.strip():
                continue
            in_header = False

        if line.strip() == "§":
            if buffer:
                entries.append(" ".join(buffer).strip())
                buffer = []
        else:
            buffer.append(line.strip())

    if buffer:
        entries.append(" ".join(buffer).strip())

    return {
        "file": str(path),
        "profile": path.parent.parent.name,
        "target": target,
        "total_entries": len(entries),
        "entries": [
            {"index": i, "text": e} for i, e in enumerate(entries) if e
        ],
    }


def discover_memory_files(base: str = PROFILES_GLOB) -> list[Path]:
    """Find all MEMORY.md and USER.md files across profiles (directory iteration, not glob)."""
    files = []
    base_path = Path(base)
    if not base_path.exists():
        return files
    for profile_dir in base_path.iterdir():
        if not profile_dir.is_dir():
            continue
        for fname in ("MEMORY.md", "USER.md"):
            fpath = profile_dir / "memories" / fname
            if fpath.exists():
                files.append(fpath)
    return files


# ─── Scanners ────────────────────────────────────────────────────────────────

def find_contradictions(memory_data: list[dict], contradiction_keywords: dict[tuple[str, str], str] | None = None) -> list[dict]:
    """
    Find entries that semantically contradict each other using keyword
    pair heuristics. v0: keyword-based. Future: embedding similarity.
    """
    contradiction_keywords = contradiction_keywords or CONTRADICTION_KEYWORDS
    findings = []
    all_entries = []
    for md in memory_data:
        for entry in md["entries"]:
            all_entries.append({**entry, "profile": md["profile"], "target": md["target"]})

    for (kw_a, kw_b), reason in contradiction_keywords.items():
        group_a = [e for e in all_entries if kw_a.lower() in e["text"].lower()]
        group_b = [e for e in all_entries if kw_b.lower() in e["text"].lower()]
        for e_a in group_a:
            for e_b in group_b:
                # Skip same-entry matches (single entries containing both keywords)
                if e_a["profile"] == e_b["profile"] and e_a["target"] == e_b["target"] and e_a["index"] == e_b["index"]:
                    continue
                if e_a["profile"] == e_b["profile"] and e_a["target"] == e_b["target"]:
                    findings.append({
                        "reason": reason,
                        "keywords": (kw_a, kw_b),
                        "entry_a": {"profile": e_a["profile"], "target": e_a["target"], "index": e_a["index"], "text": e_a["text"][:120]},
                        "entry_b": {"profile": e_b["profile"], "target": e_b["target"], "index": e_b["index"], "text": e_b["text"][:120]},
                    })
    return findings


def find_orphan_references(memory_data: list[dict], orphan_keywords: list[str] | None = None) -> list[dict]:
    """Find entries referencing known dead/stale projects or profiles."""
    orphan_keywords = orphan_keywords or ORPHAN_KEYWORDS
    findings = []
    for md in memory_data:
        for entry in md["entries"]:
            text_lower = entry["text"].lower()
            for keyword in orphan_keywords:
                if keyword.lower() in text_lower:
                    # Only flag if the entry ALSO doesn't acknowledge it's dead
                    if "dead" in text_lower or "shelved" in text_lower or "phased out" in text_lower:
                        continue
                    findings.append({
                        "profile": md["profile"],
                        "target": md["target"],
                        "index": entry["index"],
                        "keyword": keyword,
                        "text": entry["text"][:120],
                    })
    return findings


def find_duplicate_content(memory_data: list[dict], threshold: float = 0.85) -> list[dict]:
    """Find entries with near-identical content across profiles."""
    from difflib import SequenceMatcher
    findings = []
    all_entries = []
    for md in memory_data:
        for entry in md["entries"]:
            all_entries.append({**entry, "profile": md["profile"], "target": md["target"]})

    for i in range(len(all_entries)):
        for j in range(i + 1, len(all_entries)):
            if all_entries[i]["profile"] == all_entries[j]["profile"] and all_entries[i]["target"] == all_entries[j]["target"]:
                sim = SequenceMatcher(None, all_entries[i]["text"], all_entries[j]["text"]).ratio()
                if sim > threshold:
                    findings.append({
                        "similarity": round(sim, 2),
                        "entry_a": {"profile": all_entries[i]["profile"], "index": all_entries[i]["index"], "text": all_entries[i]["text"][:100]},
                        "entry_b": {"profile": all_entries[i]["profile"], "index": all_entries[j]["index"], "text": all_entries[j]["text"][:100]},
                    })
    return findings


def get_topic_distribution(memory_data: list[dict]) -> dict[str, int]:
    """Get topic distribution across all memory entries (keyword-based)."""
    topics = Counter()
    topic_keywords = {
        "hermes": ["hermes", "profile", "swarm", "delegation", "gateway"],
        "github": ["github", "git", "repo", "commit", "pr", "push"],
        "antaeus": ["antaeus"],
        "eva": ["eva", "evidence", "verification"],
        "models": ["deepseek", "openai", "gemini", "model", "gpt"],
        "skills": ["skill", "skill_manage", "SKILL.md"],
        "memory": ["memory", "memories"],
        "ssh/macbook": ["ssh", "macbook", "mac"],
        "telegram": ["telegram", "dm", "channel"],
        "worker-patterns": ["worker-pattern", "worker pattern"],
        "naming": ["repo name", "public", "private", "lab"],
    }
    for md in memory_data:
        for entry in md["entries"]:
            text_lower = entry["text"].lower()
            for topic, kws in topic_keywords.items():
                if any(kw in text_lower for kw in kws):
                    topics[topic] += 1
    return dict(topics.most_common(20))


# ─── Main scan ───────────────────────────────────────────────────────────────

def run_scan(base: str = PROFILES_GLOB, vault: str | Path | None = None) -> dict:
    """Run all memory scanners and return structured findings."""
    settings = (
        load_settings(vault).get("memory", {})
        if vault is not None
        else load_settings().get("memory", {})
    )
    orphan_keywords = list(settings.get("orphan_keywords", ORPHAN_KEYWORDS))
    contradiction_keywords = {
        (item[0], item[1]): item[2]
        for item in settings.get("contradiction_keywords", [])
        if isinstance(item, list) and len(item) >= 3
    } or CONTRADICTION_KEYWORDS
    duplicate_threshold = float(settings.get("duplicate_similarity_threshold", 0.85))
    files = discover_memory_files(base)
    memory_data = [parse_memory_file(f) for f in files]

    total_entries = sum(md["total_entries"] for md in memory_data)
    profiles = {md["profile"] for md in memory_data}

    return {
        "scanner": "memory",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "files_scanned": len(files),
            "profiles": sorted(profiles),
            "total_entries": total_entries,
        },
        "memory_data": memory_data,
        "contradictions": find_contradictions(memory_data, contradiction_keywords),
        "orphan_references": find_orphan_references(memory_data, orphan_keywords),
        "duplicates": find_duplicate_content(memory_data, duplicate_threshold),
        "topics": get_topic_distribution(memory_data),
        "health": {
            "contradiction_scanner": "keyword-based heuristics only",
            "orphan_detection": f"settings keyword list ({len(orphan_keywords)} terms)",
            "duplicate_similarity_threshold": duplicate_threshold,
            "staleness_scanner": "disabled — filesystem mtime only, markdown has no per-entry timestamps",
        },
    }


def main() -> None:
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else PROFILES_GLOB
    result = run_scan(base)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
