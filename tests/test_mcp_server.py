from __future__ import annotations

import json
from pathlib import Path

from eva.common import atomic_write_json
from eva.mcp_server import (
    _bounded_details,
    _handle_json_rpc_message,
    eva_compile_remediation_bridge,
    eva_scan_health_bridge,
    tool_names,
)


def _write_state_db(profile: Path) -> None:
    import sqlite3

    profile.mkdir(parents=True)
    con = sqlite3.connect(profile / "state.db")
    con.execute(
        "CREATE TABLE sessions "
        "(id TEXT PRIMARY KEY, source TEXT, model TEXT, title TEXT, started_at REAL)"
    )
    con.execute(
        "CREATE TABLE messages "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, "
        "tool_calls TEXT, tool_name TEXT, timestamp REAL)"
    )
    con.execute("INSERT INTO sessions VALUES ('s1','cli','m','Title', 2000000000)")
    con.execute(
        "INSERT INTO messages(session_id, role, content, tool_calls, tool_name, timestamp) "
        "VALUES ('s1','tool','Traceback error','','terminal',2000000001)"
    )
    con.commit()
    con.close()


def test_tool_names_are_stable() -> None:
    assert tool_names() == ("eva_scan_health", "eva_compile_remediation")


def test_scan_health_bridge_defaults_to_no_write(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    vault = tmp_path / "vault"
    _write_state_db(profiles / "p1")

    result = eva_scan_health_bridge(
        {"scan": "sessions", "profiles_dir": str(profiles), "vault": str(vault), "days": 99999}
    )

    assert result["status"] == "ok"
    assert result["scan"] == "sessions"
    assert result["summary"]["tool_failures_found"] == 1
    assert not vault.exists()


def test_compile_remediation_bridge_defaults_to_no_write(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    vault = tmp_path / "vault"
    _write_state_db(profiles / "p1")

    result = eva_compile_remediation_bridge(
        {"profiles_dir": str(profiles), "vault": str(vault), "days": 99999}
    )

    assert result["status"] == "ok"
    assert result["used_latest_scan"] is False
    assert "remediation_plan" in result
    assert "notification_summary" in result
    assert not vault.exists()


def test_compile_remediation_bridge_uses_latest_scan_without_rescan(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    vault = tmp_path / "vault"
    _write_state_db(profiles / "p1")
    scan_bundle = {
        "scanner": "combined",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "memory": {"summary": {"entries_scanned": 1}},
        "sessions": {"summary": {"tool_failures_found": 7}, "repeated_failures": []},
        "skills": {"summary": {"duplicate_name_count": 0}},
        "configs": {"summary": {"drift_findings": 0}},
        "memory_provider": {"summary": {}},
        "proposal_summary": {"proposals": []},
    }
    atomic_write_json(vault / "briefs" / "latest-scan.json", scan_bundle)

    result = eva_compile_remediation_bridge(
        {"profiles_dir": str(profiles), "vault": str(vault), "write": True}
    )

    assert result["status"] == "ok"
    assert result["used_latest_scan"] is True
    assert result["summary"]["sessions"]["tool_failures_found"] == 7
    assert (vault / "plans" / "latest-plan.json").exists()
    assert (vault / "health" / "latest-notification.txt").exists()


def test_bounded_details_truncates_large_lists() -> None:
    details = _bounded_details({"rows": [{"i": i} for i in range(5)]}, limit=2)

    assert details["rows"] == [{"i": 0}, {"i": 1}, {"_truncated": True, "shown": 2, "total": 5}]


def test_json_rpc_fallback_lists_and_calls_tools(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    _write_state_db(profiles / "p1")

    listed = _handle_json_rpc_message({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert listed is not None
    tools = listed["result"]["tools"]
    assert {tool["name"] for tool in tools} == set(tool_names())

    called = _handle_json_rpc_message(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "eva_scan_health",
                "arguments": {"scan": "sessions", "profiles_dir": str(profiles), "days": 99999},
            },
        }
    )
    assert called is not None
    payload = json.loads(called["result"]["content"][0]["text"])
    assert payload["summary"]["tool_failures_found"] == 1
