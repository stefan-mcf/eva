from eva.validators import validate_proposal_actionability, validate_scan_completeness


def test_validate_scan_completeness_blocks_degraded_profiles():
    scan = {'scanner':'combined','timestamp':'t','sessions':{'health':{'degraded_profiles':['p1']}}, 'proposal_summary': {'proposals': []}}
    result = validate_scan_completeness(scan)
    assert result['blocking'] is True
    assert result['status'] == 'failed'


def test_validate_proposal_actionability_finds_missing_and_suppressed_kinds():
    scan = {'scanner':'combined','timestamp':'t','sessions': {'summary': {'tool_failures_found': 3}}, 'proposal_summary': {'proposals': []}}
    result = validate_proposal_actionability(scan, {'proposals': {'suppressed_kinds':['tool_failure_triage']}})
    assert 'tool_failure_triage' in result['missing_proposal_kinds']
    assert 'tool_failure_triage' in result['suppressed_active_kinds']
    assert result['status'] == 'failed'
