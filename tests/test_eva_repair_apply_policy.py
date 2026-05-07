from eva.repair.applier import apply_repair_bundle
from eva.repair.io import write_repair_bundle
from eva.repair.planner import draft_repair_bundle


def test_apply_safe_review_packet_and_block_human_gated_bundle(tmp_path):
    safe = draft_repair_bundle({'id':'p1','kind':'tool_failure_triage','title':'Triage','evidence':[{'x':1}]}, {'timestamp':'t'}, vault=tmp_path)
    safe['status'] = 'approved'
    write_repair_bundle(safe, tmp_path)
    outcome = apply_repair_bundle(safe, vault=tmp_path)
    assert outcome['status'] == 'applied'
    assert outcome['actions_succeeded']
    assert (tmp_path / outcome['actions_succeeded'][0]['path']).exists()

    gated = draft_repair_bundle({'id':'p2','kind':'memory_merge','title':'Memory','evidence':[]}, {'timestamp':'t'}, vault=tmp_path)
    gated['status'] = 'approved'
    blocked = apply_repair_bundle(gated, vault=tmp_path, force=True)
    assert blocked['status'] == 'blocked'
    assert 'not auto-applicable' in blocked['blocked_reason']
