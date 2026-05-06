from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from eva.compilers.compile_remediation_plan import (
    compile_notification_summary,
    compile_remediation_plan,
    render_remediation_plan_markdown,
    write_remediation_plan,
)
from eva.loop import run_all


def _rich_scan_bundle() -> dict:
    proposals = [
        {"id": "p-memory", "kind": "memory_merge", "title": "Review contradictory memory entries"},
        {"id": "p-tool", "kind": "tool_failure_runbook", "title": "Create runbooks"},
        {"id": "p-skill", "kind": "skill_restructure", "title": "Restructure oversized skills"},
        {"id": "p-config", "kind": "config_alignment", "title": "Review config drift"},
        {"id": "p-profile", "kind": "operator_profile_review", "title": "Approve profile"},
    ]
    return {
        "scanner": "combined",
        "timestamp": "2026-05-06T00:00:00+00:00",
        "memory": {
            "contradictions": [{"reason": "conflict"}],
            "orphan_references": [{"reference": "old"}],
            "duplicates": [{"a": "one", "b": "two"}],
        },
        "sessions": {
            "summary": {"tool_failures_found": 4, "corrections_found": 2},
            "repeated_failures": [{"tool": "terminal", "count": 4}],
        },
        "skills": {
            "oversized_skills": [{"name": "big"}],
            "high_patch_frequency": [{"name": "patched"}],
            "stale_skills": [{"name": "stale"}],
            "duplicate_names": [{"name": "dup"}],
        },
        "configs": {"drift": [{"profile": "p1", "key": "model.default"}]},
        "operator_profile": {"preferences": {"style": ["concise"]}},
        "proposal_summary": {"proposals": proposals, "written": []},
    }


def test_compile_remediation_plan_schema_and_safety() -> None:
    plan = compile_remediation_plan({"scanner": "combined", "timestamp": "2026-05-06T00:00:00+00:00"})

    assert plan["schema"] == "eva-remediation-plan/v1"
    assert plan["source_scan_timestamp"] == "2026-05-06T00:00:00+00:00"
    assert plan["safety"]["auto_apply"] is False
    assert plan["safety"]["source_mutation_allowed"] is False
    assert plan["tranches"][0]["id"] == "TR-0"
    assert plan["tranches"][0]["approval_required"] is False


def test_compile_remediation_plan_maps_findings_to_ordered_tranches() -> None:
    plan = compile_remediation_plan(_rich_scan_bundle(), vault="/tmp/eva-vault")

    tranche_ids = [tranche["id"] for tranche in plan["tranches"]]
    assert tranche_ids == ["TR-0", "TR-1", "TR-2", "TR-3", "TR-4", "TR-5", "TR-6", "TR-7"]
    assert plan["summary"]["finding_counts"]["memory_contradictions"] == 1
    assert plan["summary"]["proposal_count"] == 5
    by_id = {tranche["id"]: tranche for tranche in plan["tranches"]}
    assert by_id["TR-2"]["source_proposal_ids"] == ["p-skill"]
    assert by_id["TR-4"]["approval_required"] is True
    assert by_id["TR-5"]["approval_required"] is True
    assert by_id["TR-6"]["approval_required"] is True
    unsafe_fragments = (" rm ", "sed -i", "patch ", "git commit", "mv ", "cp ")
    for tranche in plan["tranches"]:
        for command in tranche["commands"]:
            assert not any(fragment in command for fragment in unsafe_fragments)


def test_render_remediation_plan_markdown_contains_checklist() -> None:
    plan = compile_remediation_plan(_rich_scan_bundle(), vault="/tmp/eva-vault")
    markdown = render_remediation_plan_markdown(plan)

    assert "# EVA Remediation Plan" in markdown
    assert "EVA does not apply fixes automatically" in markdown
    assert "## TR-0: Verify scan completeness" in markdown
    assert "- [ ]" in markdown
    assert "plans/latest-plan.md" in markdown


def test_write_remediation_plan_writes_latest_and_timestamped_artifacts(tmp_path: Path) -> None:
    plan = compile_remediation_plan(_rich_scan_bundle(), vault=tmp_path)
    paths = write_remediation_plan(plan, tmp_path, stamp="20260506T000000Z")

    assert (tmp_path / "plans" / "latest-plan.json").exists()
    assert (tmp_path / "plans" / "latest-plan.md").exists()
    assert (tmp_path / "plans" / "plan-20260506T000000Z.json").exists()
    assert (tmp_path / "plans" / "plan-20260506T000000Z.md").exists()
    assert json.loads((tmp_path / "plans" / "latest-plan.json").read_text())["schema"] == "eva-remediation-plan/v1"
    assert paths["latest_json"].endswith("plans/latest-plan.json")


def test_loop_no_write_compiles_plan_without_creating_vault(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    vault = tmp_path / "vault"
    profiles.mkdir()

    bundle = run_all(vault=vault, profiles_dir=profiles, write=False)

    assert bundle["remediation_plan"]["schema"] == "eva-remediation-plan/v1"
    assert not vault.exists()


def test_loop_write_mode_persists_plan_and_notification_artifacts(tmp_path: Path) -> None:
    profiles = tmp_path / "profiles"
    vault = tmp_path / "vault"
    profiles.mkdir()

    bundle = run_all(vault=vault, profiles_dir=profiles, write=True)

    assert (vault / "plans" / "latest-plan.json").exists()
    assert (vault / "plans" / "latest-plan.md").exists()
    assert (vault / "health" / "latest-notification.txt").exists()
    assert bundle["remediation_plan_paths"]["latest_markdown"].endswith("plans/latest-plan.md")
    assert "EVA scan complete." in (vault / "health" / "latest-notification.txt").read_text()


def test_compile_notification_summary_is_chat_sized() -> None:
    plan = compile_remediation_plan(_rich_scan_bundle(), vault="/tmp/eva-vault")
    summary = compile_notification_summary(plan)

    assert summary.startswith("EVA scan complete.")
    assert "Pending proposals: 5" in summary
    assert "Plan:" in summary
    assert len(summary) < 1000


def test_eva_compile_plan_cli_prints_json_and_markdown(tmp_path: Path) -> None:
    scan = tmp_path / "scan.json"
    scan.write_text(json.dumps(_rich_scan_bundle()), encoding="utf-8")

    json_result = subprocess.run(
        [sys.executable, "-m", "eva.compilers.compile_remediation_plan", str(scan), "--json"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(json_result.stdout)["schema"] == "eva-remediation-plan/v1"

    markdown_result = subprocess.run(
        [sys.executable, "-m", "eva.compilers.compile_remediation_plan", str(scan), "--markdown"],
        text=True,
        capture_output=True,
        check=True,
    )
    assert "# EVA Remediation Plan" in markdown_result.stdout


def test_eva_compile_plan_cli_write_requires_vault(tmp_path: Path) -> None:
    scan = tmp_path / "scan.json"
    scan.write_text(json.dumps(_rich_scan_bundle()), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "eva.compilers.compile_remediation_plan", str(scan), "--write"],
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "--vault is required" in result.stderr
