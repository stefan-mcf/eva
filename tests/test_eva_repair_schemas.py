from eva.repair.schemas import REPAIR_BUNDLE_SCHEMA, validate_repair_bundle


def _bundle():
    return {
        'schema': REPAIR_BUNDLE_SCHEMA,
        'id': 'b1',
        'created_at': '2026-05-07T00:00:00+00:00',
        'source_scan_timestamp': '2026-05-07T00:00:00+00:00',
        'source_proposal_id': 'p1',
        'source_proposal_kind': 'tool_failure_triage',
        'status': 'drafted',
        'risk': 'low',
        'target_class': 'eva_review_packet',
        'requires_human_gate': False,
        'auto_apply_allowed': True,
        'summary': 'draft packet',
        'evidence': [],
        'affected_paths': [],
        'planned_actions': [{'action_type':'write_review_packet'}],
        'preconditions': [],
        'rollback': [],
        'verification': [],
        'operator_decision': {'state':'not_required'},
    }


def test_validate_repair_bundle_accepts_complete_bundle():
    assert validate_repair_bundle(_bundle()) == []


def test_validate_repair_bundle_reports_missing_and_invalid_fields():
    bundle = _bundle()
    bundle.pop('id')
    bundle['risk'] = 'extreme'
    errors = validate_repair_bundle(bundle)
    assert any('missing required field: id' in e for e in errors)
    assert any('invalid risk' in e for e in errors)



def test_validate_repair_bundle_blocks_auto_apply_for_human_gated_target():
    bundle = _bundle()
    bundle['target_class'] = 'hermes_memory'
    bundle['requires_human_gate'] = True
    bundle['auto_apply_allowed'] = True
    errors = validate_repair_bundle(bundle)
    assert any('auto_apply_allowed cannot be true' in e for e in errors)


def test_validate_repair_bundle_rejects_malformed_actions_and_evidence():
    bundle = _bundle()
    bundle['evidence'] = 'not-a-list'
    bundle['planned_actions'] = [123, {}]
    errors = validate_repair_bundle(bundle)
    assert 'evidence must be a list' in errors
    assert 'planned_actions[0] must be an object' in errors
    assert 'planned_actions[1] missing action_type' in errors
