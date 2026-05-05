from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from eva.compilers.compile_brief import compile_brief
from eva.loop import run_all
from eva.proposers.propose_patches import generate_proposals, record_outcome, write_pending
from eva.scanners import scan_configs, scan_memory, scan_sessions, scan_shyftr, scan_skills


def _write_state_db(profile: Path, messages: list[tuple[str, str, str | None, float]]) -> None:
    profile.mkdir(parents=True)
    db = profile / "state.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE sessions "
        "(id TEXT PRIMARY KEY, source TEXT, model TEXT, title TEXT, started_at REAL)"
    )
    con.execute(
        "CREATE TABLE messages "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content TEXT, "
        "tool_calls TEXT, tool_name TEXT, timestamp REAL)"
    )
    con.execute("INSERT INTO sessions VALUES ('s1','telegram','m','Title', 2000000000)")
    for role, content, tool_name, ts in messages:
        con.execute(
            "INSERT INTO messages(session_id, role, content, tool_calls, tool_name, timestamp) "
            "VALUES (?,?,?,?,?,?)",
            ("s1", role, content, "", tool_name, ts),
        )
    con.commit()
    con.close()


def _write_settings(vault: Path, settings: dict) -> None:
    path = vault / "context" / "settings.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(settings), encoding="utf-8")


def test_session_scanner_detects_corrections_and_failures(tmp_path: Path) -> None:
    _write_state_db(
        tmp_path / "p1",
        [
            ("user", "Actually, don't do that.", None, 2000000001),
            ("tool", "Traceback error", "terminal", 2000000002),
        ],
    )

    result = scan_sessions.run_scan(tmp_path, days=99999)
    assert result["summary"]["corrections_found"] == 1
    assert result["summary"]["tool_failures_found"] == 1


def test_session_scanner_uses_settings_threshold(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_settings(vault, {"sessions": {"window_days": 99999, "repeated_failure_threshold": 2}})
    _write_state_db(
        tmp_path / "profiles" / "p1",
        [
            ("tool", "Traceback error", "terminal", 2000000001),
            ("tool", "Traceback error", "terminal", 2000000002),
        ],
    )

    result = scan_sessions.run_scan(tmp_path / "profiles", vault=vault)
    assert result["summary"]["window_days"] == 99999
    assert result["summary"]["repeated_failure_threshold"] == 2
    assert result["repeated_failures"] == [{"tool": "terminal", "count": 2}]


def test_skill_scanner_flags_oversized(tmp_path: Path) -> None:
    skill = tmp_path / "p1" / "skills" / "big" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: big\ndescription: Big\n---\n" + "x" * 81000)
    result = scan_skills.run_scan(tmp_path)
    assert result["summary"]["oversized_count"] == 1
    assert result["oversized_skills"][0]["name"] == "big"


def test_skill_scanner_uses_settings_threshold(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_settings(vault, {"skills": {"oversized_bytes": 10}})
    skill = tmp_path / "profiles" / "p1" / "skills" / "small" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: small\ndescription: Small\n---\nsmall")

    result = scan_skills.run_scan(tmp_path / "profiles", vault=vault)
    assert result["summary"]["oversized_count"] == 1
    assert result["health"]["oversized_threshold_bytes"] == 10


def test_memory_scanner_uses_settings_threshold(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    _write_settings(vault, {"memory": {"duplicate_similarity_threshold": 0.1}})
    memories = tmp_path / "profiles" / "p1" / "memories"
    memories.mkdir(parents=True)
    memories.joinpath("MEMORY.md").write_text("alpha beta\n§\nalpha beta gamma\n", encoding="utf-8")

    result = scan_memory.run_scan(str(tmp_path / "profiles"), vault=vault)
    assert result["duplicates"]
    assert result["health"]["duplicate_similarity_threshold"] == 0.1


def test_shyftr_scanner_reports_cell_diagnostics(tmp_path: Path) -> None:
    cell = tmp_path / "cell"
    (cell / "config").mkdir(parents=True)
    (cell / "ledger").mkdir(parents=True)
    (cell / "charges").mkdir(parents=True)
    (cell / "config" / "cell_manifest.json").write_text(json.dumps({"cell_id": "c"}), encoding="utf-8")
    (cell / "ledger" / "diagnostic_logs.jsonl").write_text(
        json.dumps({"operation": "pack", "status": "ok"}) + "\n"
        + json.dumps({"operation": "signal", "status": "accepted"}) + "\n",
        encoding="utf-8",
    )
    (cell / "charges" / "approved.jsonl").write_text(json.dumps({"trace_id": "trace-1"}) + "\n", encoding="utf-8")

    result = scan_shyftr.run_scan(cell)

    assert result["summary"]["cell_id"] == "c"
    assert result["summary"]["approved_charges"] == 1
    assert result["summary"]["diagnostic_operations"] == {"pack": 1, "signal": 1}
    result["summary"]["profile_modes"] = {"antaeus-terminal-side": "runtime_primary"}
    brief = compile_brief(result)
    assert "ShyftR" in brief
    assert "antaeus-terminal-side=runtime_primary" in brief


def test_config_scanner_detects_group_drift(tmp_path: Path) -> None:
    for name, model in [("antaeus-terminal", "a"), ("antaeus-terminal-side", "b")]:
        cfg = tmp_path / name / "config.yaml"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(f"model:\n  default: {model}\n  provider: deepseek\nagent:\n  max_turns: 50\n")
    result = scan_configs.run_scan(tmp_path)
    assert any(d["key"] == "model.default" for d in result["drift"])


def test_compile_brief_and_proposal_outcome(tmp_path: Path) -> None:
    bundle = {
        "scanner": "combined",
        "timestamp": "2026-05-05T00:00:00Z",
        "memory": {
            "scanner": "memory",
            "summary": {"files_scanned": 1, "profiles": ["p"], "total_entries": 1},
            "contradictions": [{"reason": "x"}],
            "orphan_references": [],
            "duplicates": [],
        },
        "sessions": {
            "scanner": "sessions",
            "summary": {
                "messages_scanned": 2,
                "profiles_scanned": 1,
                "window_days": 30,
                "corrections_found": 1,
                "tool_failures_found": 0,
                "skill_patches_found": 0,
            },
            "repeated_failures": [],
        },
        "skills": {
            "scanner": "skills",
            "summary": {
                "skills_scanned": 1,
                "profiles_scanned": 1,
                "oversized_count": 0,
                "stale_count": 0,
                "duplicate_name_count": 0,
            },
            "oversized_skills": [],
        },
        "configs": {"scanner": "configs", "summary": {"profiles_scanned": 1, "drift_findings": 0}, "drift": []},
    }
    brief = compile_brief(bundle)
    assert "EVA Scan" in brief
    proposals = generate_proposals(bundle)
    paths = write_pending(proposals, tmp_path)
    assert paths
    moved = record_outcome(proposals[0]["id"], "applied", tmp_path, "ok")
    assert moved.exists()
    assert json.loads(moved.read_text())["status"] == "applied"


def test_loop_no_write_does_not_create_or_modify_files(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    vault = tmp_path / "vault"
    _write_state_db(
        profiles / "p1",
        [
            ("user", "Actually, prefer dry runs.", None, 2000000001),
            ("tool", "Traceback error", "terminal", 2000000002),
        ],
    )
    memories = profiles / "p1" / "memories"
    memories.mkdir(parents=True)
    memories.joinpath("MEMORY.md").write_text("concise terminal-readable output\n", encoding="utf-8")

    bundle = run_all(vault=vault, profiles_dir=profiles, days=99999, write=False)

    assert "brief" in bundle
    assert not vault.exists()
