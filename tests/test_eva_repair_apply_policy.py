from pathlib import Path

from eva.common import atomic_write_json, ensure_vault
from eva.repair.applier import apply_repair_bundle
from eva.repair.io import write_repair_bundle
from eva.repair.planner import draft_repair_bundle


def test_apply_safe_review_packet_and_block_human_gated_bundle(tmp_path):
    safe = draft_repair_bundle(
        {"id": "p1", "kind": "tool_failure_triage", "title": "Triage", "evidence": [{"x": 1}]},
        {"timestamp": "t"},
        vault=tmp_path,
    )
    safe["status"] = "approved"
    write_repair_bundle(safe, tmp_path)
    outcome = apply_repair_bundle(safe, vault=tmp_path)
    assert outcome["status"] == "applied"
    assert outcome["actions_succeeded"]
    assert (tmp_path / outcome["actions_succeeded"][0]["path"]).exists()

    gated = draft_repair_bundle(
        {"id": "p2", "kind": "memory_merge", "title": "Memory", "evidence": []},
        {"timestamp": "t"},
        vault=tmp_path,
    )
    gated["status"] = "approved"
    blocked = apply_repair_bundle(gated, vault=tmp_path, force=True)
    assert blocked["status"] == "blocked"
    assert "not auto-applicable" in blocked["blocked_reason"]


def test_auto_apply_blocks_review_packet_path_escape(tmp_path: Path):
    bundle = draft_repair_bundle(
        {"id": "p1", "kind": "tool_failure_triage", "title": "Triage", "evidence": [{"x": 1}]},
        {"timestamp": "t"},
        vault=tmp_path,
    )
    bundle["planned_actions"][0]["target_path"] = "../escaped.md"

    outcome = apply_repair_bundle(bundle, vault=tmp_path)

    assert outcome["status"] == "failed"
    assert "escapes the EVA vault" in outcome["actions_failed"][0]["reason"]
    assert not (tmp_path.parent / "escaped.md").exists()


def test_apply_eva_generated_artifact_only_inside_vault(tmp_path: Path):
    bundle = draft_repair_bundle(
        {
            "id": "artifact1",
            "kind": "repair_ledger",
            "title": "Ledger",
            "summary": "Generated ledger",
            "payload": {"content": "# Ledger\n"},
            "evidence": [{"source": "test"}],
        },
        {"timestamp": "t"},
        vault=tmp_path,
    )

    outcome = apply_repair_bundle(bundle, vault=tmp_path)

    assert outcome["status"] == "applied"
    assert (tmp_path / "repairs" / "generated").is_dir()
    written = tmp_path / outcome["actions_succeeded"][0]["path"]
    assert written.exists()
    assert written.read_text().startswith("# Ledger")


def test_auto_apply_blocks_generated_artifact_path_escape(tmp_path: Path):
    bundle = draft_repair_bundle(
        {
            "id": "artifact2",
            "kind": "repair_ledger",
            "title": "Ledger",
            "summary": "Generated ledger",
            "payload": {"content": "# Ledger\n"},
            "evidence": [{"source": "test"}],
        },
        {"timestamp": "t"},
        vault=tmp_path,
    )
    bundle["planned_actions"][0]["target_path"] = "../generated-escape.md"

    outcome = apply_repair_bundle(bundle, vault=tmp_path)

    assert outcome["status"] == "failed"
    assert "escapes the EVA vault" in outcome["actions_failed"][0]["reason"]
    assert not (tmp_path.parent / "generated-escape.md").exists()


def test_apply_json_generated_artifact(tmp_path: Path):
    bundle = draft_repair_bundle(
        {
            "id": "artifact3",
            "kind": "repair_ledger",
            "title": "Ledger",
            "summary": "Generated ledger",
            "payload": {"content": "ledger-json"},
            "evidence": [{"source": "test"}],
        },
        {"timestamp": "t"},
        vault=tmp_path,
    )
    bundle["planned_actions"][0]["target_path"] = "repairs/generated/ledger.json"

    outcome = apply_repair_bundle(bundle, vault=tmp_path)

    assert outcome["status"] == "applied"
    written = tmp_path / outcome["actions_succeeded"][0]["path"]
    assert written.exists()
    assert '"content": "ledger-json"' in written.read_text()


def test_apply_deterministic_rejected_proposal_state(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(
        vault / "proposals" / "pending" / "target.json",
        {"id": "target", "kind": "tool_failure_triage", "title": "Target", "status": "pending"},
    )
    bundle = draft_repair_bundle(
        {
            "id": "state1",
            "kind": "proposal_rejected",
            "title": "Reject false positive",
            "summary": "Scanner evidence proves this is a false positive.",
            "payload": {
                "target_proposal_id": "target",
                "outcome": "rejected",
                "false_positive": True,
            },
            "evidence": [{"classification": "false_positive", "source": "scanner"}],
        },
        {"timestamp": "t"},
        vault=vault,
    )

    outcome = apply_repair_bundle(bundle, vault=vault)

    assert outcome["status"] == "applied"
    assert (vault / "proposals" / "rejected" / "target.json").exists()
    assert not (vault / "proposals" / "pending" / "target.json").exists()
    assert bundle["affected_paths"] == ["proposals/rejected/target.json"]


def test_apply_deterministic_superseded_proposal_state(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(
        vault / "proposals" / "pending" / "target.json",
        {"id": "target", "kind": "tool_failure_triage", "title": "Target", "status": "pending"},
    )
    atomic_write_json(
        vault / "proposals" / "pending" / "replacement.json",
        {
            "id": "replacement",
            "kind": "tool_failure_triage",
            "title": "Replacement",
            "status": "pending",
        },
    )
    bundle = draft_repair_bundle(
        {
            "id": "state-superseded",
            "kind": "proposal_superseded",
            "title": "Mark superseded",
            "summary": "Exact replacement proposal exists.",
            "payload": {
                "target_proposal_id": "target",
                "outcome": "superseded",
                "replacement_proposal_id": "replacement",
            },
            "evidence": [{"target": "target", "replacement": "replacement"}],
        },
        {"timestamp": "t"},
        vault=vault,
    )

    outcome = apply_repair_bundle(bundle, vault=vault)

    assert outcome["status"] == "applied"
    assert (vault / "proposals" / "superseded" / "target.json").exists()
    assert (vault / "proposals" / "pending" / "replacement.json").exists()


def test_invalid_proposal_state_target_is_caught_as_action_failure(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    bundle = draft_repair_bundle(
        {
            "id": "state-missing-target",
            "kind": "proposal_rejected",
            "title": "Missing target",
            "payload": {
                "target_proposal_id": "missing",
                "outcome": "rejected",
                "false_positive": True,
            },
            "evidence": [{"classification": "false_positive"}],
        },
        {"timestamp": "t"},
        vault=vault,
    )

    outcome = apply_repair_bundle(bundle, vault=vault)

    assert outcome["status"] == "failed"
    assert "proposal not found" in outcome["actions_failed"][0]["reason"]


def test_blocks_non_deterministic_proposal_state_even_with_force(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(
        vault / "proposals" / "pending" / "target.json",
        {"id": "target", "kind": "tool_failure_triage", "title": "Target", "status": "pending"},
    )
    bundle = draft_repair_bundle(
        {
            "id": "state2",
            "kind": "proposal_rejected",
            "title": "Reject without evidence",
            "payload": {"target_proposal_id": "target", "outcome": "rejected"},
            "evidence": [],
        },
        {"timestamp": "t"},
        vault=vault,
    )
    bundle["status"] = "approved"

    outcome = apply_repair_bundle(bundle, vault=vault, force=True)

    assert outcome["status"] == "blocked"
    assert "proposal-state update is not deterministic" in outcome["blocked_reason"]
    assert (vault / "proposals" / "pending" / "target.json").exists()


def test_apply_applied_proposal_state_requires_existing_verification_artifact(tmp_path: Path):
    vault = ensure_vault(tmp_path)
    atomic_write_json(
        vault / "proposals" / "pending" / "target.json",
        {"id": "target", "kind": "tool_failure_triage", "title": "Target", "status": "pending"},
    )
    bundle = draft_repair_bundle(
        {
            "id": "state3",
            "kind": "proposal_applied",
            "title": "Mark applied",
            "payload": {
                "target_proposal_id": "target",
                "outcome": "applied",
                "verification_artifact": "repairs/applied/missing.json",
            },
            "evidence": [{"verification": "repairs/applied/missing.json"}],
        },
        {"timestamp": "t"},
        vault=vault,
    )

    outcome = apply_repair_bundle(bundle, vault=vault)

    assert outcome["status"] == "failed"
    assert "verification artifact not found" in outcome["actions_failed"][0]["reason"]
    assert (vault / "proposals" / "pending" / "target.json").exists()
