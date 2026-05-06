"""Shared helpers for EVA scanners and compilers."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERMES_PROFILES_DIR = Path(os.environ.get("EVA_HERMES_PROFILES_DIR", Path.home() / ".hermes" / "profiles")).expanduser()
EVA_PROFILE_DIR = Path(os.environ.get("EVA_PROFILE_DIR", HERMES_PROFILES_DIR / "eva")).expanduser()
EVA_VAULT_DIR = Path(os.environ.get("EVA_VAULT_DIR", EVA_PROFILE_DIR / "workspace" / "eva-vault")).expanduser()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def ensure_vault(vault: Path = EVA_VAULT_DIR) -> Path:
    for rel in [
        "context",
        "evidence",
        "proposals/pending",
        "proposals/applied",
        "proposals/rejected",
        "briefs",
        "plans",
        "health",
    ]:
        (vault / rel).mkdir(parents=True, exist_ok=True)
    for rel in ["evidence/corrections.jsonl", "evidence/failures.jsonl", "evidence/successes.jsonl"]:
        p = vault / rel
        if not p.exists():
            p.write_text("", encoding="utf-8")
    return vault


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
            count += 1
    return count


def profile_dirs(base: Path = HERMES_PROFILES_DIR) -> list[Path]:
    if not base.exists():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir())


def safe_snippet(text: str | None, limit: int = 220) -> str:
    if not text:
        return ""
    one_line = " ".join(str(text).split())
    return one_line[: limit - 1] + "…" if len(one_line) > limit else one_line
