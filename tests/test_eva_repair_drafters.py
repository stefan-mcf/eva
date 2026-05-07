from eva.repair.drafters import draft_actions_for_proposal


def test_human_gated_drafters_are_inert():
    actions = draft_actions_for_proposal({'id':'p1','kind':'memory_cleanup','title':'Memory','evidence':[{'entry':'secret'}]})
    assert actions
    assert all(a.get('requires_approval') for a in actions)
    assert not any(a.get('action_type') == 'apply_memory_operation' for a in actions)


def test_tool_triage_drafter_writes_review_packet():
    actions = draft_actions_for_proposal({'id':'p1','kind':'tool_failure_triage','title':'Triage','evidence':[]})
    assert actions[0]['action_type'] == 'write_review_packet'
