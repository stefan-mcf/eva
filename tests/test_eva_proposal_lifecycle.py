import pytest

from eva.proposals import PROPOSAL_STATES, normalize_proposal_state, proposal_dedupe_key


def test_normalize_proposal_state_accepts_known_states():
    assert {normalize_proposal_state(s.upper()) for s in PROPOSAL_STATES} == PROPOSAL_STATES


def test_normalize_proposal_state_rejects_unknown_state():
    with pytest.raises(ValueError):
        normalize_proposal_state('maybe')


def test_proposal_dedupe_key_prefers_metadata():
    assert proposal_dedupe_key({'kind':'k','title':'t','metadata':{'dedupe_key':'custom'}}) == 'custom'
    assert proposal_dedupe_key({'kind':'k','title':'t'}) == 'k:t'
