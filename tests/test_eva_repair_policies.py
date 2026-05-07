from eva.repair.policies import classify_repair_policy, is_deterministic_proposal_state_update


def test_recommended_policy_classes():
    assert classify_repair_policy({"kind": "tool_failure_triage"}) == {
        "target_class": "eva_review_packet",
        "risk": "low",
        "requires_human_gate": False,
        "auto_apply_allowed": True,
    }
    assert classify_repair_policy({"kind": "repair_ledger"})["target_class"] == "eva_generated_artifact"
    assert classify_repair_policy({"kind": "memory_cleanup"}) == {
        "target_class": "hermes_memory",
        "risk": "high",
        "requires_human_gate": True,
        "auto_apply_allowed": False,
    }
    assert classify_repair_policy({"kind": "config_alignment"})["target_class"] == "hermes_profile_config"
    assert classify_repair_policy({"kind": "operator_profile_review"})["target_class"] == "operator_profile"
    assert classify_repair_policy({"kind": "unknown"})["risk"] == "forbidden"


def test_proposal_state_policy_requires_evidence_keyed_constraints():
    unsafe = {
        "kind": "proposal_rejected",
        "payload": {"target_proposal_id": "p1", "outcome": "rejected"},
        "evidence": [{"x": 1}],
    }
    assert is_deterministic_proposal_state_update(unsafe) is False
    assert classify_repair_policy(unsafe) == {
        "target_class": "eva_proposal_state",
        "risk": "medium",
        "requires_human_gate": True,
        "auto_apply_allowed": False,
    }

    safe_reject = {
        "kind": "proposal_rejected",
        "payload": {"target_proposal_id": "p1", "outcome": "rejected", "false_positive": True},
        "evidence": [{"classification": "false_positive"}],
    }
    assert is_deterministic_proposal_state_update(safe_reject) is True
    assert classify_repair_policy(safe_reject)["auto_apply_allowed"] is True

    safe_superseded = {
        "kind": "proposal_superseded",
        "payload": {
            "target_proposal_id": "p1",
            "outcome": "superseded",
            "replacement_proposal_id": "p2",
        },
        "evidence": [{"replacement": "p2"}],
    }
    assert is_deterministic_proposal_state_update(safe_superseded) is True

    safe_applied = {
        "kind": "proposal_applied",
        "payload": {
            "target_proposal_id": "p1",
            "outcome": "applied",
            "verification_artifact": "repairs/applied/p1-outcome.json",
        },
        "evidence": [{"verification_artifact": "repairs/applied/p1-outcome.json"}],
    }
    assert is_deterministic_proposal_state_update(safe_applied) is True
