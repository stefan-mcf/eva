"""EVA session scanner for Hermes SQLite state stores."""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from eva.common import (
    HERMES_PROFILES_DIR,
    append_jsonl,
    ensure_vault,
    profile_dirs,
    safe_snippet,
    utc_now,
)
from eva.settings import load_settings

CORRECTION_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\bactually\b",
        r"\bno[, ]+",
        r"\bdon't\b",
        r"\bdo not\b",
        r"\bnever\b",
        r"\bremember this\b",
        r"\binstead\b",
        r"\bnot what I asked\b",
        r"\bwrong\b",
    ]
]
FAILURE_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"traceback \(most recent call last\)",
        r"\bexception\b",
        r"\berror\b",
        r"exit_code[^\n]{0,40}[1-9]",
        r"command not found",
        r"permission denied",
        r"timeout",
        r"failed",
    ]
]


def _connect_ro(db: Path) -> sqlite3.Connection:
    # immutable=1 prevents SQLite from creating -wal/-shm sidecar files while
    # EVA is scanning live Hermes profile state as a read-only evidence source.
    return sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)


def _iso(ts: float | int | None) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return None


def _cutoff(days: int) -> float:
    return (datetime.now(timezone.utc) - timedelta(days=days)).timestamp()


def discover_state_dbs(base: Path = HERMES_PROFILES_DIR) -> list[Path]:
    return [p / "state.db" for p in profile_dirs(base) if (p / "state.db").exists()]


def _rows(db: Path, days: int) -> list[sqlite3.Row]:
    con = _connect_ro(db)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(
            """
            SELECT m.id, m.session_id, m.role, m.content, m.tool_calls, m.tool_name, m.timestamp,
                   s.title, s.source, s.model
            FROM messages m
            LEFT JOIN sessions s ON s.id = m.session_id
            WHERE m.timestamp >= ?
            ORDER BY m.timestamp DESC
            LIMIT 5000
            """,
            (_cutoff(days),),
        ).fetchall()
    finally:
        con.close()


def scan_database(db: Path, days: int = 30, repeated_failure_threshold: int = 3) -> dict[str, Any]:
    profile = db.parent.name
    corrections: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    skill_patches: list[dict[str, Any]] = []
    by_tool: Counter[str] = Counter()
    by_pattern: Counter[str] = Counter()
    rows_seen = 0

    try:
        rows = _rows(db, days)
    except Exception as exc:
        return {
            "profile": profile,
            "database": str(db),
            "status": "degraded",
            "error": f"{type(exc).__name__}: {exc}",
            "messages_scanned": 0,
            "corrections": [],
            "tool_failures": [],
            "skill_patches": [],
        }

    for row in rows:
        rows_seen += 1
        content = row["content"] or ""
        tool_calls = row["tool_calls"] or ""
        blob = f"{content}\n{tool_calls}"
        base = {
            "profile": profile,
            "session_id": row["session_id"],
            "message_id": row["id"],
            "timestamp": _iso(row["timestamp"]),
            "title": row["title"],
            "source": row["source"],
        }

        if row["role"] == "user":
            matched = [p.pattern for p in CORRECTION_PATTERNS if p.search(content)]
            if matched:
                corrections.append({**base, "patterns": matched[:3], "text": safe_snippet(content)})

        if _is_tool_failure_context(row["role"], row["tool_name"], tool_calls, content):
            for pat in FAILURE_PATTERNS:
                if not pat.search(blob):
                    continue
                tool = row["tool_name"] or _infer_tool(tool_calls) or _infer_tool(content) or "unknown"
                rec = {
                    **base,
                    "tool": tool,
                    "pattern": pat.pattern,
                    "text": safe_snippet(blob),
                }
                failures.append(rec)
                by_tool[tool] += 1
                by_pattern[pat.pattern] += 1
                break

        if "skill_manage" in blob and "patch" in blob:
            skill_patches.append({**base, "tool": "skill_manage", "text": safe_snippet(blob)})

    repeated = [
        {"tool": tool, "count": count}
        for tool, count in by_tool.most_common()
        if count >= repeated_failure_threshold
    ]
    return {
        "profile": profile,
        "database": str(db),
        "status": "ok",
        "messages_scanned": rows_seen,
        "corrections": corrections[:100],
        "tool_failures": failures[:200],
        "repeated_failures": repeated,
        "failure_patterns": dict(by_pattern.most_common(10)),
        "skill_patches": skill_patches[:100],
    }


def _is_tool_failure_context(role: str | None, tool_name: str | None, tool_calls: str, content: str) -> bool:
    if role == "tool" or tool_name:
        return True
    if tool_calls and _infer_tool(tool_calls):
        return True
    stripped = (content or "").lstrip()
    if not stripped.startswith(("{", "[")):
        return False
    try:
        parsed = json.loads(stripped)
    except Exception:
        return False
    if isinstance(parsed, dict):
        return any(k in parsed for k in ("exit_code", "error", "stderr", "tool", "tool_name"))
    return False


def _infer_tool(tool_calls: str) -> str | None:
    try:
        parsed = json.loads(tool_calls)
    except Exception:
        return None
    if isinstance(parsed, list) and parsed:
        first = parsed[0]
        if isinstance(first, dict):
            return (
                first.get("function", {}).get("name")
                or first.get("name")
                or first.get("tool_name")
                or first.get("tool")
            )
    if isinstance(parsed, dict):
        explicit = (
            parsed.get("tool_name")
            or parsed.get("tool")
            or parsed.get("name")
            or parsed.get("function", {}).get("name")
        )
        if explicit:
            return explicit
        if "todos" in parsed:
            return "todo"
        if "session_id" in parsed and ("output" in parsed or "exit_code" in parsed):
            return "process"
        if "output" in parsed or "exit_code" in parsed or "stderr" in parsed:
            return "terminal"
        if "content" in parsed and "total_lines" in parsed:
            return "read_file"
        if "matches" in parsed or "files" in parsed:
            return "search_files"
        if "diff" in parsed or "files_modified" in parsed:
            return "patch"
    return None


def run_scan(
    base: str | Path = HERMES_PROFILES_DIR,
    days: int | None = None,
    vault: str | Path | None = None,
) -> dict[str, Any]:
    settings = (
        load_settings(vault).get("sessions", {})
        if vault is not None
        else load_settings().get("sessions", {})
    )
    days = int(days if days is not None else settings.get("window_days", 30))
    repeated_failure_threshold = int(settings.get("repeated_failure_threshold", 3))
    failure_sample_limit = int(settings.get("failure_sample_limit", 50))
    dbs = discover_state_dbs(Path(base))
    profiles = [
        scan_database(db, days=days, repeated_failure_threshold=repeated_failure_threshold)
        for db in dbs
    ]
    corrections = [c for p in profiles for c in p.get("corrections", [])]
    failures = [f for p in profiles for f in p.get("tool_failures", [])]
    skill_patches = [s for p in profiles for s in p.get("skill_patches", [])]
    repeated_by_tool = Counter()
    for f in failures:
        repeated_by_tool[f.get("tool", "unknown")] += 1

    result = {
        "scanner": "sessions",
        "timestamp": utc_now(),
        "summary": {
            "profiles_scanned": len(profiles),
            "databases_scanned": len(dbs),
            "messages_scanned": sum(p.get("messages_scanned", 0) for p in profiles),
            "corrections_found": len(corrections),
            "tool_failures_found": len(failures),
            "skill_patches_found": len(skill_patches),
            "window_days": days,
            "repeated_failure_threshold": repeated_failure_threshold,
        },
        "profiles": profiles,
        "corrections": corrections[:200],
        "tool_failures": failures[:failure_sample_limit],
        "repeated_failures": [
            {"tool": t, "count": c}
            for t, c in repeated_by_tool.most_common()
            if c >= repeated_failure_threshold
        ],
        "skill_patches": skill_patches[:200],
        "health": {
            "session_scanner": "sqlite state.db read-only scan",
            "degraded_profiles": [p for p in profiles if p.get("status") != "ok"],
            "tool_failure_context": "failure patterns are counted only for tool-role/tool-name/tool-call/structured-tool-result messages",
            "failure_sample_limit": failure_sample_limit,
        },
    }
    if vault:
        v = ensure_vault(Path(vault))
        append_jsonl(v / "evidence" / "corrections.jsonl", corrections)
        append_jsonl(v / "evidence" / "failures.jsonl", failures)
    return result


def main() -> None:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else HERMES_PROFILES_DIR
    print(json.dumps(run_scan(base), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
