from pathlib import Path

from eva.repair.io import write_repair_bundle
from eva.repair.planner import draft_repair_bundle


def test_draft_repair_bundle_classifies_known_and_unknown_proposals(tmp_path: Path):
    safe = draft_repair_bundle({'id':'p1','kind':'tool_failure_triage','title':'Triage','evidence':[]}, {'timestamp':'t'}, vault=tmp_path)
    assert safe['target_class'] == 'eva_review_packet'
    assert safe['auto_apply_allowed'] is True
    gated = draft_repair_bundle({'id':'p2','kind':'memory_merge','title':'Memory','evidence':[]}, {'timestamp':'t'}, vault=tmp_path)
    assert gated['target_class'] == 'hermes_memory'
    assert gated['requires_human_gate'] is True
    unknown = draft_repair_bundle({'id':'p3','kind':'???','title':'Unknown','evidence':[]}, {'timestamp':'t'}, vault=tmp_path)
    assert unknown['risk'] == 'forbidden'


def test_write_repair_bundle_writes_draft(tmp_path: Path):
    bundle = draft_repair_bundle({'id':'p1','kind':'tool_failure_triage','title':'Triage','evidence':[]}, {'timestamp':'t'}, vault=tmp_path)
    path = write_repair_bundle(bundle, tmp_path)
    assert path.exists()
    assert path.parent.name == 'drafts'
