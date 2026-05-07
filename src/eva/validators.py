"""Core EVA scan/proposal validators."""
from __future__ import annotations

from typing import Any

EVIDENCE_TO_PROPOSAL_KIND = {
    "memory_contradictions": "memory_merge",
    "memory_orphan_references": "memory_cleanup",
    "session_repeated_failures": "tool_failure_runbook",
    "session_tool_failures": "tool_failure_triage",
    "session_corrections": "session_correction_review",
    "session_skill_patches": "session_skill_patch_review",
    "skill_oversized": "skill_restructure",
    "skill_high_patch_frequency": "skill_rewrite",
    "skill_duplicate_names": "skill_duplicate_review",
    "skill_stale": "skill_stale_review",
    "config_drift": "config_alignment",
    "operator_profile_preferences": "operator_profile_review",
}


def _len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def evidence_counts(scan_bundle: dict[str, Any]) -> dict[str, int]:
    memory = scan_bundle.get("memory", {}) if isinstance(scan_bundle.get("memory", {}), dict) else {}
    sessions = scan_bundle.get("sessions", {}) if isinstance(scan_bundle.get("sessions", {}), dict) else {}
    skills = scan_bundle.get("skills", {}) if isinstance(scan_bundle.get("skills", {}), dict) else {}
    configs = scan_bundle.get("configs", {}) if isinstance(scan_bundle.get("configs", {}), dict) else {}
    session_summary = sessions.get("summary", {}) if isinstance(sessions.get("summary", {}), dict) else {}
    skill_summary = skills.get("summary", {}) if isinstance(skills.get("summary", {}), dict) else {}
    operator_profile = scan_bundle.get("operator_profile", {}) if isinstance(scan_bundle.get("operator_profile", {}), dict) else {}
    return {
        "memory_contradictions": _len(memory.get("contradictions")),
        "memory_orphan_references": _len(memory.get("orphan_references")),
        "session_repeated_failures": _len(sessions.get("repeated_failures")),
        "session_tool_failures": int(session_summary.get("tool_failures_found", 0) or _len(sessions.get("tool_failures"))),
        "session_corrections": int(session_summary.get("corrections_found", 0) or _len(sessions.get("corrections"))),
        "session_skill_patches": int(session_summary.get("skill_patches_found", 0) or _len(sessions.get("skill_patches"))),
        "skill_oversized": _len(skills.get("oversized_skills")),
        "skill_high_patch_frequency": _len(skills.get("high_patch_frequency")),
        "skill_duplicate_names": _len(skills.get("duplicate_skill_names")) or _len(skills.get("duplicate_names")) or int(skill_summary.get("duplicate_name_count", 0) or 0),
        "skill_stale": _len(skills.get("stale_skills")) or int(skill_summary.get("stale_count", 0) or 0),
        "config_drift": _len(configs.get("drift")),
        "operator_profile_preferences": 1 if operator_profile.get("preferences") else 0,
    }


def _has_degraded_markers(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in {"degraded", "partial", "error", "errors", "warnings"} and item:
                return True
            if key_text == "status" and str(item).lower() in {"degraded", "partial", "error", "failed"}:
                return True
            if _has_degraded_markers(item):
                return True
    elif isinstance(value, list):
        return any(_has_degraded_markers(item) for item in value)
    return False


def validate_scan_completeness(scan_bundle: dict[str, Any], *, expected_vault: str | None = None, expected_profiles_dir: str | None = None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    def add(name: str, ok: bool, severity: str = "error", detail: str = "") -> None:
        checks.append({"name": name, "ok": ok, "severity": severity, "detail": detail})
    add("scan_is_dict", isinstance(scan_bundle, dict))
    add("timestamp_present", bool(scan_bundle.get("timestamp")))
    add("scanner_combined", scan_bundle.get("scanner") == "combined", "warning", str(scan_bundle.get("scanner")))
    degraded_profiles = scan_bundle.get("sessions", {}).get("health", {}).get("degraded_profiles", []) if isinstance(scan_bundle.get("sessions"), dict) else []
    add("no_degraded_profiles", not bool(degraded_profiles), "error", str(degraded_profiles))
    add("no_degraded_markers", not _has_degraded_markers(scan_bundle), "error")
    proposals = scan_bundle.get("proposal_summary", {}).get("proposals", []) if isinstance(scan_bundle.get("proposal_summary"), dict) else []
    add("proposal_list_present", isinstance(proposals, list), "warning")
    blocking = any((not c["ok"]) and c["severity"] == "error" for c in checks)
    status = "failed" if blocking else "warning" if any(not c["ok"] for c in checks) else "ok"
    return {"status": status, "blocking": blocking, "checks": checks, "expected_vault": expected_vault, "expected_profiles_dir": expected_profiles_dir}


def validate_proposal_actionability(scan_bundle: dict[str, Any], settings: dict[str, Any] | None = None) -> dict[str, Any]:
    counts = evidence_counts(scan_bundle)
    proposals = scan_bundle.get("proposal_summary", {}).get("proposals", []) if isinstance(scan_bundle.get("proposal_summary"), dict) else []
    proposal_kinds = {str(p.get("kind")) for p in proposals if isinstance(p, dict) and p.get("kind")}
    suppressed = set((settings or {}).get("proposals", {}).get("suppressed_kinds", []))
    expected_active = {kind for evidence, kind in EVIDENCE_TO_PROPOSAL_KIND.items() if counts.get(evidence, 0) > 0}
    missing = sorted(expected_active - proposal_kinds)
    suppressed_active = sorted(expected_active & suppressed)
    status = "failed" if missing or suppressed_active else "ok"
    return {
        "status": status,
        "blocking": bool(suppressed_active),
        "evidence_counts": counts,
        "proposal_kinds": sorted(proposal_kinds),
        "expected_active_proposal_kinds": sorted(expected_active),
        "missing_proposal_kinds": missing,
        "suppressed_active_kinds": suppressed_active,
    }
