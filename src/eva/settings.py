"""Runtime-tunable EVA settings.

Values can be changed without code edits by writing JSON to
`~/.hermes/profiles/eva/workspace/eva-vault/context/settings.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eva.common import EVA_VAULT_DIR

DEFAULT_SETTINGS: dict[str, Any] = {
    "memory": {
        "contradiction_keywords": [
            ["always", "never", "Direct contradiction"],
            ["public", "private", "Visibility contradiction"],
            ["ssh", "do not ssh", "SSH access contradiction"],
            ["antaeus", "dead", "Project lifecycle contradiction"],
            ["lab", "no lab", "Naming convention contradiction"],
        ],
        "orphan_keywords": ["antaeus", "antaeus-terminal", "antaeus-terminal-side", "courier", "shyftr"],
        "duplicate_similarity_threshold": 0.85,
        "contradiction_context_exceptions": [
            {
                "keywords": ["public", "private"],
                "phrases": ["private wip", "public-facing", "public release", "private-to-public"],
            },
            {
                "keywords": ["antaeus", "dead"],
                "phrases": ["shelved", "dead", "phased out", "not active"],
            },
            {
                "keywords": ["lab", "no lab"],
                "phrases": ["naming", "repo", "boundary", "public"],
            },
        ],
    },
    "skills": {
        "oversized_bytes": 80000,
        "stale_days": 30,
        "high_patch_threshold": 3,
        "include_archived_in_priority": False,
        "archive_path_markers": ["/.archive/", "/archive/"],
    },
    "sessions": {
        "window_days": 30,
        "repeated_failure_threshold": 3,
        "failure_sample_limit": 50,
        "tool_failure_roles": ["tool"],
    },
    "configs": {
        "role_groups": {
            "swarm": {"prefixes": ["swarm"]},
            "worker": {"prefixes": ["worker-"]},
            "antaeus-terminal": {"prefixes": ["antaeus-terminal"]},
            "default": {"names": ["default"]},
            "eva": {"names": ["eva"]},
            "courier": {"names": ["courier"]},
            "reviewer": {"names": ["reviewer"]}
        },
        "ignored_drift": []
    },
    "brief": {
        "max_examples": 10,
        "style": "telegram-concise",
    },
    "proposals": {
        "acceptance_bonus": 0.2,
        "rejection_penalty": 0.3,
    },
    "operator": {
        "name": "Operator",
    },
}


def load_settings(vault: str | Path = EVA_VAULT_DIR) -> dict[str, Any]:
    settings = json.loads(json.dumps(DEFAULT_SETTINGS))
    path = Path(vault) / "context" / "settings.json"
    if path.exists():
        try:
            override = json.loads(path.read_text(encoding="utf-8"))
            _merge(settings, override)
        except Exception:
            # Scanner health reports should catch malformed settings later; keep defaults safe.
            pass
    return settings


def _merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
