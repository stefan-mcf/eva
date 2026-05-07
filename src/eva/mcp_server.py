"""MCP bridge for EVA health scans.

The bridge is intentionally read/proposal-first. It exposes scan and remediation
summary surfaces, but it does not expose proposal application or profile/config
mutation. ``write`` defaults to False for strict dry-run behavior.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO

from eva.common import EVA_VAULT_DIR, HERMES_PROFILES_DIR, read_json
from eva.compilers.compile_remediation_plan import (
    compile_notification_summary,
    compile_remediation_plan,
    write_notification_summary,
    write_remediation_plan,
)
from eva.loop import run_all
from eva.scanners import scan_configs, scan_memory, scan_memory_provider, scan_sessions, scan_skills

TOOL_NAMES = ("eva_scan_health", "eva_compile_remediation")
SCAN_KINDS = ("all", "memory", "sessions", "skills", "configs", "memory_provider")
DEFAULT_DETAIL_LIMIT = 25

JsonArgs = str | bytes | bytearray | Mapping[str, Any]


def eva_scan_health_bridge(args: JsonArgs | None = None) -> dict[str, Any]:
    """Run an EVA scan and return a bounded JSON-safe summary."""

    payload = _load_payload(args or {})
    scan = str(payload.get("scan") or "all")
    include_details = bool(payload.get("include_details", False))
    detail_limit = _optional_int(payload.get("detail_limit")) or DEFAULT_DETAIL_LIMIT
    result = _run_scan(
        scan=scan,
        profiles_dir=payload.get("profiles_dir"),
        vault=payload.get("vault"),
        days=payload.get("days"),
        write=bool(payload.get("write", False)),
    )
    return _bounded_result(
        "eva_scan_health", scan, result, include_details=include_details, detail_limit=detail_limit
    )


def eva_compile_remediation_bridge(args: JsonArgs | None = None) -> dict[str, Any]:
    """Run EVA's scan-to-remediation compiler and return operator-safe outputs."""

    payload = _load_payload(args or {})
    include_bundle = bool(payload.get("include_bundle", False))
    detail_limit = _optional_int(payload.get("detail_limit")) or DEFAULT_DETAIL_LIMIT
    write = bool(payload.get("write", False))
    vault_path = Path(payload.get("vault") or EVA_VAULT_DIR).expanduser()
    profiles_path = Path(payload.get("profiles_dir") or HERMES_PROFILES_DIR).expanduser()
    latest_scan = vault_path / "briefs" / "latest-scan.json"
    used_latest_scan = False
    if not bool(payload.get("rescan", False)) and latest_scan.exists():
        bundle = read_json(latest_scan)
        used_latest_scan = True
        plan = compile_remediation_plan(bundle, vault_path if write else None)
        if write:
            bundle["remediation_plan"] = plan
            bundle["remediation_plan_paths"] = write_remediation_plan(plan, vault_path)
            bundle["notification_summary_path"] = write_notification_summary(plan, vault_path)
    else:
        bundle = run_all(
            vault=vault_path,
            profiles_dir=profiles_path,
            days=_optional_int(payload.get("days")),
            write=write,
        )
        plan = bundle.get("remediation_plan", {})
    response: dict[str, Any] = {
        "tool": "eva_compile_remediation",
        "status": "ok",
        "write": write,
        "used_latest_scan": used_latest_scan,
        "summary": _summarize_bundle(bundle),
        "remediation_plan": plan,
        "notification_summary": compile_notification_summary(plan) if isinstance(plan, dict) else "",
        "written_paths": {
            "remediation_plan_paths": bundle.get("remediation_plan_paths", {}),
            "notification_summary_path": bundle.get("notification_summary_path"),
        },
    }
    if include_bundle:
        response["bundle"] = _bounded_details(bundle, limit=detail_limit)
    return response


def create_mcp_server() -> Any:
    """Create a FastMCP server for EVA tools."""

    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError("EVA MCP bridge requires optional package 'mcp'.") from exc

    server = FastMCP("eva")

    @server.tool(name="eva_scan_health")
    def eva_scan_health_tool(
        scan: str = "all",
        profiles_dir: str | None = None,
        vault: str | None = None,
        days: int | None = None,
        write: bool = False,
        include_details: bool = False,
        detail_limit: int = DEFAULT_DETAIL_LIMIT,
    ) -> dict[str, Any]:
        return eva_scan_health_bridge(
            {
                "scan": scan,
                "profiles_dir": profiles_dir,
                "vault": vault,
                "days": days,
                "write": write,
                "include_details": include_details,
                "detail_limit": detail_limit,
            }
        )

    @server.tool(name="eva_compile_remediation")
    def eva_compile_remediation_tool(
        profiles_dir: str | None = None,
        vault: str | None = None,
        days: int | None = None,
        write: bool = False,
        include_bundle: bool = False,
        rescan: bool = False,
        detail_limit: int = DEFAULT_DETAIL_LIMIT,
    ) -> dict[str, Any]:
        return eva_compile_remediation_bridge(
            {
                "profiles_dir": profiles_dir,
                "vault": vault,
                "days": days,
                "write": write,
                "include_bundle": include_bundle,
                "rescan": rescan,
                "detail_limit": detail_limit,
            }
        )

    return server


def tool_names() -> tuple[str, ...]:
    return TOOL_NAMES


def main() -> None:
    """Run the stdio MCP server.

    FastMCP is preferred. Set ``EVA_FORCE_STDIO_FALLBACK=1`` to use the tiny
    JSON-RPC fallback for launch/protocol smoke tests.
    """

    if os.getenv("EVA_FORCE_STDIO_FALLBACK") == "1":
        _run_json_rpc_stdio(sys.stdin, sys.stdout)
        return
    try:
        server = create_mcp_server()
    except RuntimeError:
        _run_json_rpc_stdio(sys.stdin, sys.stdout)
        return
    server.run()


def _run_scan(
    *,
    scan: str,
    profiles_dir: str | Path | None,
    vault: str | Path | None,
    days: Any,
    write: bool,
) -> dict[str, Any]:
    profiles = Path(profiles_dir or HERMES_PROFILES_DIR).expanduser()
    vault_path = Path(vault or EVA_VAULT_DIR).expanduser()
    scan = scan.strip().lower()
    if scan not in SCAN_KINDS:
        raise ValueError(f"scan must be one of {', '.join(SCAN_KINDS)}")
    if scan == "all":
        return run_all(vault=vault_path, profiles_dir=profiles, days=_optional_int(days), write=write)
    if scan == "memory":
        return scan_memory.run_scan(str(profiles), vault=vault_path if write else None)
    if scan == "sessions":
        return scan_sessions.run_scan(profiles, days=_optional_int(days), vault=vault_path if write else None)
    if scan == "skills":
        return scan_skills.run_scan(profiles, vault=vault_path if write else None)
    if scan == "configs":
        return scan_configs.run_scan(profiles, vault=vault_path if write else None)
    if scan == "memory_provider":
        return scan_memory_provider.run_scan(vault=vault_path if write else None)
    raise AssertionError("unreachable")


def _bounded_result(
    tool: str, scan: str, result: dict[str, Any], *, include_details: bool, detail_limit: int = DEFAULT_DETAIL_LIMIT
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "tool": tool,
        "status": "ok",
        "scan": scan,
        "summary": _summarize_bundle(result) if scan == "all" else result.get("summary", {}),
        "health": result.get("health", {}),
    }
    if include_details:
        response["details"] = _bounded_details(result, limit=detail_limit)
    return response


def _bounded_details(value: Any, *, limit: int = DEFAULT_DETAIL_LIMIT) -> Any:
    """Return MCP-safe detail payloads without multi-MB evidence dumps.

    Full scans can contain thousands of session/skill evidence rows. Returning all
    of them through MCP regularly pushes tool calls past Hermes' configured MCP
    timeout. Keep summaries, health, paths, and the first N records of large
    lists, with explicit truncation metadata so operators know to inspect the
    vault artifacts for full evidence.
    """

    limit = max(0, int(limit))
    return _trim_for_mcp(_json_safe(value), limit=limit)


def _trim_for_mcp(value: Any, *, limit: int) -> Any:
    if isinstance(value, list):
        trimmed = [_trim_for_mcp(item, limit=limit) for item in value[:limit]]
        if len(value) > limit:
            trimmed.append({"_truncated": True, "shown": limit, "total": len(value)})
        return trimmed
    if isinstance(value, dict):
        return {str(key): _trim_for_mcp(item, limit=limit) for key, item in value.items()}
    return value


def _summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    if bundle.get("scanner") != "combined":
        return dict(bundle.get("summary", {}))
    return {
        "memory": bundle.get("memory", {}).get("summary", {}),
        "sessions": bundle.get("sessions", {}).get("summary", {}),
        "skills": bundle.get("skills", {}).get("summary", {}),
        "configs": bundle.get("configs", {}).get("summary", {}),
        "memory_provider": bundle.get("memory_provider", {}).get("summary", {}),
        "proposal_count": len(bundle.get("proposal_summary", {}).get("proposals", [])),
    }


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _load_payload(args: JsonArgs) -> dict[str, Any]:
    if isinstance(args, Mapping):
        return dict(args)
    if isinstance(args, str | bytes | bytearray):
        decoded = json.loads(args)
        if not isinstance(decoded, dict):
            raise ValueError("args must decode to a JSON object")
        return decoded
    raise TypeError("args must be a JSON object string or mapping")


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))


def _run_json_rpc_stdio(stdin: TextIO, stdout: TextIO) -> None:
    for line in stdin:
        if not line.strip():
            continue
        response = _handle_json_rpc_message(json.loads(line))
        if response is not None:
            stdout.write(json.dumps(response, sort_keys=True) + "\n")
            stdout.flush()


def _handle_json_rpc_message(message: dict[str, Any]) -> dict[str, Any] | None:
    request_id = message.get("id")
    method = message.get("method")
    try:
        if method == "initialize":
            return _json_rpc_result(
                request_id,
                {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "eva", "version": "0.1.0"},
                    "capabilities": {"tools": {}},
                },
            )
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return _json_rpc_result(request_id, {"tools": _tool_descriptors()})
        if method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            if name == "eva_scan_health":
                payload = eva_scan_health_bridge(arguments)
            elif name == "eva_compile_remediation":
                payload = eva_compile_remediation_bridge(arguments)
            else:
                raise ValueError(f"unknown tool: {name}")
            return _json_rpc_result(
                request_id,
                {"content": [{"type": "text", "text": json.dumps(payload, sort_keys=True)}], "isError": False},
            )
        raise ValueError(f"unsupported method: {method}")
    except Exception as exc:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}}


def _json_rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _tool_descriptors() -> list[dict[str, Any]]:
    scan_schema = {
        "type": "object",
        "properties": {
            "scan": {"type": "string", "enum": list(SCAN_KINDS)},
            "profiles_dir": {"type": "string"},
            "vault": {"type": "string"},
            "days": {"type": "integer"},
            "write": {"type": "boolean", "default": False},
            "include_details": {"type": "boolean", "default": False},
            "detail_limit": {"type": "integer", "default": DEFAULT_DETAIL_LIMIT},
        },
    }
    remediation_schema = {
        "type": "object",
        "properties": {
            "profiles_dir": {"type": "string"},
            "vault": {"type": "string"},
            "days": {"type": "integer"},
            "write": {"type": "boolean", "default": False},
            "include_bundle": {"type": "boolean", "default": False},
            "rescan": {"type": "boolean", "default": False},
            "detail_limit": {"type": "integer", "default": DEFAULT_DETAIL_LIMIT},
        },
    }
    return [
        {
            "name": "eva_scan_health",
            "description": "Run an EVA read/proposal-first health scan. Defaults to dry-run/no-write.",
            "inputSchema": scan_schema,
        },
        {
            "name": "eva_compile_remediation",
            "description": "Compile an EVA remediation plan summary. Defaults to dry-run/no-write.",
            "inputSchema": remediation_schema,
        },
    ]


if __name__ == "__main__":  # pragma: no cover
    main()
