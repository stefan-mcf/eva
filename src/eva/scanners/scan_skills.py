"""EVA skill-health scanner."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eva.common import HERMES_PROFILES_DIR, profile_dirs, utc_now
from eva.settings import load_settings

OVERSIZED_BYTES = 80_000
STALE_DAYS = 30
PATCH_RE = re.compile(r"skill_manage\([^)]*action=['\"]patch['\"]", re.I)
LOAD_RE = re.compile(r"skill_view\([^)]*name=['\"]([^'\"]+)", re.I)


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    data: dict[str, Any] = {}
    for line in text[3:end].splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        data[key.strip()] = val.strip().strip('"\'')
    return data


def discover_skill_files(base: Path = HERMES_PROFILES_DIR) -> list[Path]:
    files: list[Path] = []
    for profile in profile_dirs(base):
        skills = profile / "skills"
        if not skills.exists():
            continue
        for path in skills.rglob("SKILL.md"):
            if "/.hub/" not in str(path):
                files.append(path)
    return sorted(files)


def _profile_for_skill(path: Path) -> str:
    parts = path.parts
    if "profiles" in parts:
        idx = parts.index("profiles")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "unknown"


def _skill_name(path: Path, meta: dict[str, Any]) -> str:
    return str(meta.get("name") or path.parent.name)


def _usage_counts(base: Path = HERMES_PROFILES_DIR) -> tuple[Counter[str], Counter[str]]:
    loads: Counter[str] = Counter()
    patches: Counter[str] = Counter()
    for _db in base.glob("*/state.db"):
        # Avoid sqlite dependency here by allowing session scanner to own exact usage. For this scanner,
        # use JSON session exports when present plus profile logs as a lightweight approximation.
        pass
    for path in list(base.glob("*/sessions/*.json")) + list(base.glob("*/logs/*.log")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for name in LOAD_RE.findall(text):
            loads[name] += 1
        if PATCH_RE.search(text):
            for name in LOAD_RE.findall(text):
                patches[name] += 1
            patches["unknown"] += len(PATCH_RE.findall(text))
    return loads, patches


def run_scan(base: str | Path = HERMES_PROFILES_DIR, vault: str | Path | None = None) -> dict[str, Any]:
    base = Path(base)
    settings = (
        load_settings(vault).get("skills", {})
        if vault is not None
        else load_settings().get("skills", {})
    )
    oversized_bytes = int(settings.get("oversized_bytes", OVERSIZED_BYTES))
    stale_days = int(settings.get("stale_days", STALE_DAYS))
    high_patch_threshold = int(settings.get("high_patch_threshold", 3))
    files = discover_skill_files(base)
    loads, patches = _usage_counts(base)
    skills: list[dict[str, Any]] = []
    by_name: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    now = datetime.now(timezone.utc)

    for path in files:
        try:
            stat = path.stat()
            meta = _parse_frontmatter(path)
            name = _skill_name(path, meta)
            age_days = max(0, int((now - datetime.fromtimestamp(stat.st_mtime, timezone.utc)).days))
            rec = {
                "name": name,
                "profile": _profile_for_skill(path),
                "path": str(path),
                "description": meta.get("description", ""),
                "version": meta.get("version", ""),
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
                "age_days": age_days,
                "load_count_hint": loads[name],
                "patch_count_hint": patches[name] + (patches["unknown"] if name == "unknown" else 0),
            }
            skills.append(rec)
            by_name[name].append(rec)
        except Exception as exc:
            skills.append({"path": str(path), "status": "degraded", "error": f"{type(exc).__name__}: {exc}"})

    oversized = [s for s in skills if s.get("size_bytes", 0) >= oversized_bytes]
    stale = [s for s in skills if s.get("age_days", 0) >= stale_days and s.get("load_count_hint", 0) == 0]
    duplicate_names = [
        {"name": name, "copies": len(items), "profiles": sorted({i["profile"] for i in items})}
        for name, items in sorted(by_name.items())
        if len(items) > 1
    ]
    high_patch = [s for s in skills if s.get("patch_count_hint", 0) >= high_patch_threshold]

    return {
        "scanner": "skills",
        "timestamp": utc_now(),
        "summary": {
            "profiles_scanned": len(profile_dirs(base)),
            "skills_scanned": len(skills),
            "oversized_count": len(oversized),
            "stale_count": len(stale),
            "duplicate_name_count": len(duplicate_names),
            "high_patch_count": len(high_patch),
        },
        "oversized_skills": oversized[:100],
        "stale_skills": stale[:100],
        "duplicate_skill_names": duplicate_names[:100],
        "high_patch_frequency": high_patch[:100],
        "skills": skills[:500],
        "health": {
            "skill_scanner": "frontmatter + mtime + lightweight session/log hints",
            "stale_threshold_days": stale_days,
            "oversized_threshold_bytes": oversized_bytes,
            "high_patch_threshold": high_patch_threshold,
            "usage_precision": "best-effort until Hermes exposes skill load events as structured telemetry",
        },
    }


def main() -> None:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else HERMES_PROFILES_DIR
    print(json.dumps(run_scan(base), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
