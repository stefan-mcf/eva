from eva.repair.applier import apply_repair_bundle
from eva.repair.closeout import (
    compile_closeout_report,
    render_closeout_markdown,
    render_residual_action_plan_markdown,
    render_run_report_markdown,
    write_closeout_report,
)
from eva.repair.io import write_repair_bundle
from eva.repair.planner import draft_repair_bundle
from eva.repair.verifier import verify_repair_outcome


def test_verify_and_closeout_reports_safe_and_blocked_repairs(tmp_path):
    safe = draft_repair_bundle({'id':'p1','kind':'tool_failure_triage','title':'Triage','evidence':[]}, {'timestamp':'t'}, vault=tmp_path)
    safe['status'] = 'approved'
    write_repair_bundle(safe, tmp_path)
    outcome = apply_repair_bundle(safe, vault=tmp_path)
    verification = verify_repair_outcome(outcome, vault=tmp_path)
    assert verification['status'] == 'ok'

    blocked = draft_repair_bundle(
        {'id': 'p2', 'kind': 'config_alignment', 'title': 'Config Drift', 'evidence': []},
        {'timestamp': 't'},
        vault=tmp_path,
    )
    blocked['status'] = 'approved'
    write_repair_bundle(blocked, tmp_path)
    blocked_outcome = apply_repair_bundle(blocked, vault=tmp_path, force=True)
    assert blocked_outcome['status'] == 'blocked'

    report = compile_closeout_report(tmp_path)
    md = render_closeout_markdown(report)
    residual_md = render_residual_action_plan_markdown(report)
    run_report_md = render_run_report_markdown(report)
    paths = write_closeout_report(report, tmp_path)

    assert 'EVA Repair Closeout' in md
    assert 'Residual Action Plan' in md
    assert 'EVA Residual Action Plan' in residual_md
    assert 'EVA run complete' in run_report_md
    assert 'Found:' in run_report_md
    assert 'Fixed:' in run_report_md
    assert 'Recommended remediation plan:' in run_report_md
    assert report['summary']['applied_outcomes'] >= 1
    assert report['summary']['residual_actions'] >= 1
    assert any(item['target_class'] == 'hermes_profile_config' for item in report['residual_action_plan'])
    assert (tmp_path / 'repairs' / 'ledger' / 'latest-residual-plan.md').exists()
    assert (tmp_path / 'repairs' / 'ledger' / 'latest-residual-plan.json').exists()
    assert (tmp_path / 'repairs' / 'ledger' / 'latest-run-report.md').exists()
    assert (tmp_path / 'repairs' / 'ledger' / 'latest-run-report.json').exists()
    assert 'latest_residual_plan_markdown' in paths
    assert 'latest_run_report_markdown' in paths
