from eva.repair.applier import apply_repair_bundle
from eva.repair.closeout import compile_closeout_report, render_closeout_markdown
from eva.repair.planner import draft_repair_bundle
from eva.repair.verifier import verify_repair_outcome


def test_verify_and_closeout_reports_safe_and_blocked_repairs(tmp_path):
    safe = draft_repair_bundle({'id':'p1','kind':'tool_failure_triage','title':'Triage','evidence':[]}, {'timestamp':'t'}, vault=tmp_path)
    safe['status'] = 'approved'
    outcome = apply_repair_bundle(safe, vault=tmp_path)
    verification = verify_repair_outcome(outcome, vault=tmp_path)
    assert verification['status'] == 'ok'
    report = compile_closeout_report(tmp_path)
    md = render_closeout_markdown(report)
    assert 'EVA Repair Closeout' in md
    assert report['summary']['applied_outcomes'] >= 1
