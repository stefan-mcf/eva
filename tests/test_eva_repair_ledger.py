from eva.repair.ledger import (
    compile_repair_ledger,
    render_repair_ledger_markdown,
    write_repair_ledger,
)
from eva.repair.planner import draft_repair_bundle


def test_repair_ledger_lists_items_and_operator_actions(tmp_path):
    bundles = [draft_repair_bundle({'id':'p1','kind':'memory_merge','title':'Memory','evidence':[]}, {'timestamp':'t'}, vault=tmp_path)]
    ledger = compile_repair_ledger(bundles, source_scan_timestamp='t')
    assert ledger['schema'] == 'eva-repair-ledger/v1'
    assert ledger['items'][0]['hardening_candidate'] is False
    md = render_repair_ledger_markdown(ledger)
    assert 'Operator Actions' in md
    paths = write_repair_ledger(ledger, tmp_path, stamp='stamp')
    assert 'latest_json' in paths and 'latest_markdown' in paths
