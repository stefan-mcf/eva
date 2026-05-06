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


def _is_archived(path: Path, markers: list[str] | None = None) -> bool:
    normalized = str(path).replace("\\", "/")
    markers = markers or ["/.archive/", "/archive/"]
    return any(marker in normalized for marker in markers)


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
    include_archived_in_priority = bool(settings.get("include_archived_in_priority", False))
    archive_markers = [str(m) for m in settings.get("archive_path_markers", ["/.archive/", "/archive/"])]
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
                "is_archived": _is_archived(path, archive_markers),
            }
            skills.append(rec)
            by_name[name].append(rec)
        except Exception as exc:
            skills.append({"path": str(path), "status": "degraded", "error": f"{type(exc).__name__}: {exc}"})

    active_skills = [s for s in skills if not s.get("is_archived")]
    archived_skills = [s for s in skills if s.get("is_archived")]
    priority_pool = skills if include_archived_in_priority else active_skills
    oversized = [s for s in priority_pool if s.get("size_bytes", 0) >= oversized_bytes]
    archived_oversized = [s for s in archived_skills if s.get("size_bytes", 0) >= oversized_bytes]
    stale = [s for s in priority_pool if s.get("age_days", 0) >= stale_days and s.get("load_count_hint", 0) == 0]

    def duplicate_records(items_by_name: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for name, items in sorted(items_by_name.items()):
            real_paths = sorted({str(Path(i["path"]).resolve()) for i in items})
            if len(real_paths) <= 1:
                continue
            records.append(
                {
                    "name": name,
                    "copies": len(items),
                    "distinct_real_paths": len(real_paths),
                    "active_copies": sum(1 for i in items if not i.get("is_archived")),
                    "archived_copies": sum(1 for i in items if i.get("is_archived")),
                    "profiles": sorted({i["profile"] for i in items}),
                    "paths": sorted(i["path"] for i in items),
                    "real_paths": real_paths,
                }
            )
        return records

    active_by_name: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    archived_by_name: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for name, items in by_name.items():
        for item in items:
            (archived_by_name if item.get("is_archived") else active_by_name)[name].append(item)
    duplicate_names = duplicate_records(active_by_name)
    archived_duplicate_names = duplicate_records(archived_by_name)
    all_duplicate_names = duplicate_records(by_name)
    high_patch = [s for s in priority_pool if s.get("patch_count_hint", 0) >= high_patch_threshold]

    return {
        "scanner": "skills",
        "timestamp": utc_now(),
        "summary": {
            "profiles_scanned": len(profile_dirs(base)),
            "skills_scanned": len(skills),
            "active_skills_scanned": len(active_skills),
            "archived_skills_scanned": len(archived_skills),
            "oversized_count": len(oversized),
            "archived_oversized_count": len(archived_oversized),
            "stale_count": len(stale),
            "duplicate_name_count": len(duplicate_names),
            "archived_duplicate_name_count": len(archived_duplicate_names),
            "all_duplicate_name_count": len(all_duplicate_names),
            "high_patch_count": len(high_patch),
        },
        "oversized_skills": oversized[:100],
        "stale_skills": stale[:100],
        "duplicate_skill_names": duplicate_names[:100],
        "archived_oversized_skills": archived_oversized[:100],
        "archived_duplicate_skill_names": archived_duplicate_names[:100],
        "all_duplicate_skill_names": all_duplicate_names[:100],
        "high_patch_frequency": high_patch[:100],
        "skills": skills[:500],
        "health": {
            "skill_scanner": "frontmatter + mtime + lightweight session/log hints",
            "stale_threshold_days": stale_days,
            "oversized_threshold_bytes": oversized_bytes,
            "high_patch_threshold": high_patch_threshold,
            "include_archived_in_priority": include_archived_in_priority,
            "archive_path_markers": archive_markers,
            "usage_precision": "best-effort session/log hints; archived copies are inventoried separately from active remediation priority",
        },
    }


def main() -> None:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else HERMES_PROFILES_DIR
    print(json.dumps(run_scan(base), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
