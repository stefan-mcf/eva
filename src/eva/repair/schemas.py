"""Schemas and validators for EVA repair artifacts."""
from __future__ import annotations

from typing import Any

REPAIR_BUNDLE_SCHEMA = "eva-repair-bundle/v1"
REPAIR_LEDGER_SCHEMA = "eva-repair-ledger/v1"
REPAIR_OUTCOME_SCHEMA = "eva-repair-outcome/v1"
REPAIR_STATUSES = {"drafted", "approved", "blocked", "applied", "verified", "failed", "superseded"}
REPAIR_RISK_TIERS = {"low", "medium", "high", "forbidden"}
TARGET_CLASSES = {
    "eva_generated_artifact",
    "eva_proposal_state",
    "eva_review_packet",
    "hermes_skill",
    "hermes_memory",
    "hermes_profile_config",
    "operator_profile",
    "scheduler",
    "credential",
    "delivery_destination",
    "public_repo",
    "unknown",
}
SAFE_AUTO_APPLY_TARGET_CLASSES = {"eva_generated_artifact", "eva_proposal_state", "eva_review_packet"}
ALWAYS_HUMAN_GATED_TARGET_CLASSES = TARGET_CLASSES - SAFE_AUTO_APPLY_TARGET_CLASSES
REQUIRED_REPAIR_BUNDLE_FIELDS = {
    "schema",
    "id",
    "created_at",
    "source_scan_timestamp",
    "source_proposal_id",
    "source_proposal_kind",
    "status",
    "risk",
    "target_class",
    "requires_human_gate",
    "auto_apply_allowed",
    "summary",
    "evidence",
    "affected_paths",
    "planned_actions",
    "preconditions",
    "rollback",
    "verification",
    "operator_decision",
}


def validate_repair_bundle(bundle: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in sorted(REQUIRED_REPAIR_BUNDLE_FIELDS):
        if field not in bundle:
            errors.append(f"missing required field: {field}")
    if bundle.get("schema") != REPAIR_BUNDLE_SCHEMA:
        errors.append(f"invalid schema: {bundle.get('schema')}")
    if bundle.get("status") not in REPAIR_STATUSES:
        errors.append(f"invalid status: {bundle.get('status')}")
    if bundle.get("risk") not in REPAIR_RISK_TIERS:
        errors.append(f"invalid risk: {bundle.get('risk')}")
    if bundle.get("target_class") not in TARGET_CLASSES:
        errors.append(f"invalid target_class: {bundle.get('target_class')}")
    if not isinstance(bundle.get("requires_human_gate"), bool):
        errors.append("requires_human_gate must be a boolean")
    if not isinstance(bundle.get("auto_apply_allowed"), bool):
        errors.append("auto_apply_allowed must be a boolean")
    if not isinstance(bundle.get("evidence"), list):
        errors.append("evidence must be a list")
    if not isinstance(bundle.get("affected_paths"), list):
        errors.append("affected_paths must be a list")
    planned_actions = bundle.get("planned_actions", [])
    if not isinstance(planned_actions, list):
        errors.append("planned_actions must be a list")
    else:
        for index, action in enumerate(planned_actions):
            if not isinstance(action, dict):
                errors.append(f"planned_actions[{index}] must be an object")
            elif not action.get("action_type"):
                errors.append(f"planned_actions[{index}] missing action_type")
    if not isinstance(bundle.get("operator_decision"), dict):
        errors.append("operator_decision must be an object")
    elif not bundle.get("operator_decision", {}).get("state"):
        errors.append("operator_decision.state is required")
    if bundle.get("auto_apply_allowed") and bundle.get("target_class") in ALWAYS_HUMAN_GATED_TARGET_CLASSES:
        errors.append("auto_apply_allowed cannot be true for human-gated target class")
    if bundle.get("target_class") in ALWAYS_HUMAN_GATED_TARGET_CLASSES and not bundle.get("requires_human_gate"):
        errors.append("human-gated target class must set requires_human_gate")
    return errors
