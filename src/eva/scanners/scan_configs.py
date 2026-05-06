"""EVA config drift scanner for Hermes profiles."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from eva.common import HERMES_PROFILES_DIR, profile_dirs, utc_now
from eva.settings import load_settings

WATCH_KEYS = [
    "model.default",
    "model.provider",
    "model.base_url",
    "model.context_length",
    "agent.max_turns",
    "terminal.timeout",
    "delegation.enabled",
    "delegation.model",
    "delegation.provider",
    "delegation.base_url",
    "delegation.max_concurrent_children",
    "delegation.max_spawn_depth",
    "compression.enabled",
]


def _simple_yaml(path: Path) -> dict[str, Any]:
    """Parse the simple nested YAML style used by Hermes configs without external deps."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#") or raw.lstrip().startswith("-"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if val == "":
            node: dict[str, Any] = {}
            parent[key] = node
            stack.append((indent, node))
        else:
            parent[key] = _coerce(val)
    return root


def _coerce(value: str) -> Any:
    value = value.strip().strip('"\'')
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "none"}:
        return None
    try:
        return int(value)
    except ValueError:
        return value


def _get(data: dict[str, Any], dotted: str) -> Any:
    cur: Any = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _role_group(profile: str, role_groups: dict[str, Any] | None = None) -> str:
    for group, rule in (role_groups or {}).items():
        names = set(rule.get("names", [])) if isinstance(rule, dict) else set()
        prefixes = tuple(rule.get("prefixes", [])) if isinstance(rule, dict) else ()
        if profile in names or (prefixes and profile.startswith(prefixes)):
            return group
    if profile.startswith("swarm"):
        return "swarm"
    if profile.startswith("worker-"):
        return "worker"
    if profile.startswith("antaeus-terminal"):
        return "antaeus-terminal"
    if profile in {"default", "eva", "courier", "reviewer"}:
        return profile
    return "other"


def _is_ignored_drift(group: str, key: str, ignored: list[dict[str, Any]]) -> bool:
    for item in ignored:
        if not isinstance(item, dict):
            continue
        if item.get("role_group") in {group, "*"} and item.get("key") in {key, "*"}:
            return True
    return False


def discover_configs(base: Path = HERMES_PROFILES_DIR) -> list[Path]:
    return [p / "config.yaml" for p in profile_dirs(base) if (p / "config.yaml").exists()]


def run_scan(base: str | Path = HERMES_PROFILES_DIR, vault: str | Path | None = None) -> dict[str, Any]:
    settings = (
        load_settings(vault).get("configs", {})
        if vault is not None
        else load_settings().get("configs", {})
    )
    role_groups = settings.get("role_groups", {})
    ignored_drift = settings.get("ignored_drift", [])
    configs = []
    for path in discover_configs(Path(base)):
        profile = path.parent.name
        try:
            data = _simple_yaml(path)
            values = {key: _get(data, key) for key in WATCH_KEYS}
            configs.append({"profile": profile, "role_group": _role_group(profile, role_groups), "path": str(path), "values": values})
        except Exception as exc:
            configs.append({"profile": profile, "path": str(path), "status": "degraded", "error": f"{type(exc).__name__}: {exc}"})

    raw_drift = []
    drift = []
    by_group: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in configs:
        if c.get("values"):
            by_group[c["role_group"]].append(c)
    for group, items in sorted(by_group.items()):
        if len(items) < 2:
            continue
        for key in WATCH_KEYS:
            vals: defaultdict[str, list[str]] = defaultdict(list)
            for item in items:
                vals[repr(item["values"].get(key))].append(item["profile"])
            if len(vals) > 1:
                rec = {"role_group": group, "key": key, "values": dict(vals)}
                raw_drift.append(rec)
                if not _is_ignored_drift(group, key, ignored_drift):
                    drift.append(rec)

    model_matrix = [
        {
            "profile": c["profile"],
            "role_group": c.get("role_group"),
            "model": c.get("values", {}).get("model.default"),
            "provider": c.get("values", {}).get("model.provider"),
            "delegation": {k.split(".", 1)[1]: v for k, v in c.get("values", {}).items() if k.startswith("delegation.")},
        }
        for c in configs
        if c.get("values")
    ]

    return {
        "scanner": "configs",
        "timestamp": utc_now(),
        "summary": {
            "profiles_scanned": len(configs),
            "drift_findings": len(drift),
            "raw_drift_findings": len(raw_drift),
            "ignored_drift_findings": len(raw_drift) - len(drift),
            "watch_keys": len(WATCH_KEYS),
        },
        "model_matrix": model_matrix,
        "drift": drift[:200],
        "raw_drift": raw_drift[:200],
        "health": {
            "config_scanner": "simple YAML parser, read-only",
            "scope": "model, agent, terminal, delegation, compression",
            "role_groups_configured": sorted(role_groups),
            "ignored_drift_rules": len(ignored_drift),
        },
    }


def main() -> None:
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else HERMES_PROFILES_DIR
    print(json.dumps(run_scan(base), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
