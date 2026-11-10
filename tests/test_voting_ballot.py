from votechain import blind
from votechain.crypto import generate_keypair, public_key_hex
from votechain.voting import VotingState
from tests.voting_helpers import EID, credential_sig, ballot, open_election, tx


def voter() -> str:
    return generate_keypair()[0]


def test_valid_ballot_points() -> None:
    state, _ = open_election()
    assert state.apply(ballot(voter(), ["A", "B", "C"]), 500) is None
    t = {e.candidate_id: e.points for e in state.tally(EID)["profesor"]}
    assert t == {"A": 3, "B": 2, "C": 1, "D": 0}


def test_invalid_picks_rejected() -> None:
    state, _ = open_election()
    for picks in (["A", "A", "B"], ["A", "B"], ["A", "B", "C", "D"], [], ["A", "B", "Z"], ["A", "B", 1]):
        assert state.apply(ballot(voter(), picks), 500), picks
    assert not state.elections[EID].ballots


def test_unknown_category_and_election() -> None:
    state, _ = open_election()
    assert state.apply(ballot(voter(), ["A", "B", "C"], category="nope"), 500)
    assert state.apply(tx(voter(), "CAST_BALLOT", {"election_id": "zz", "category": "profesor", "picks": ["A", "B", "C"], "credential_sig": "1"}), 500)


def test_double_vote_rejected_only_per_category() -> None:
    state, admin = open_election()
    v = voter()
    pub = public_key_hex(v)
    assert state.apply(ballot(v, ["A", "B", "C"]), 500) is None
    assert state.apply(ballot(v, ["D", "C", "B"]), 501)
    assert state.elections[EID].ballots[(pub, "profesor")] == ["A", "B", "C"]
    # otra categoría: se arma una elección con dos categorías
    s2 = VotingState()
    from tests.voting_helpers import draft_election
    draft_election(s2, admin)
    s2.apply(tx(admin, "ADD_CATEGORY", {"election_id": EID, "category": "adm"}), 1)
    for c in "ABC":
        s2.apply(tx(admin, "ADD_CANDIDATE", {"election_id": EID, "category": "adm", "candidate_id": c, "name": c}), 1)
    assert s2.apply(tx(admin, "OPEN_ELECTION", {"election_id": EID}), 1) is None
    assert s2.apply(ballot(v, ["A", "B", "C"]), 500) is None
    assert s2.apply(ballot(v, ["C", "B", "A"], category="adm"), 500) is None


def test_not_open_rejected() -> None:
    from tests.voting_helpers import draft_election
    admin = voter()
    state = VotingState()
    draft_election(state, admin)
    assert state.apply(ballot(voter(), ["A", "B", "C"]), 500)  # draft
    state.apply(tx(admin, "OPEN_ELECTION", {"election_id": EID}), 1)
    state.apply(tx(admin, "CLOSE_ELECTION", {"election_id": EID}), 1)
    assert state.apply(ballot(voter(), ["A", "B", "C"]), 500)  # closed


def test_outside_window_rejected() -> None:
    state, _ = open_election(opens_at=100, closes_at=200)
    assert state.apply(ballot(voter(), ["A", "B", "C"]), 99)
    assert state.apply(ballot(voter(), ["A", "B", "C"]), 201)
    assert state.apply(ballot(voter(), ["A", "B", "C"]), 100) is None
    assert state.apply(ballot(voter(), ["A", "B", "C"]), 200) is None


def test_payload_has_no_personal_data() -> None:
    assert set(ballot(voter(), ["A", "B", "C"]).payload) == {"election_id", "category", "picks"}


def _raw(key: str, sig: object) -> object:
    payload = {"election_id": EID, "category": "profesor", "picks": ["A", "B", "C"], "credential_sig": sig}
    return tx(key, "CAST_BALLOT", payload)


def test_credential_required_and_checked() -> None:
    state, _ = open_election()
    v = voter()
    good = credential_sig(v)
    other_election = credential_sig(v, election_id="otra")
    other_key = credential_sig(voter())
    foreign_issuer = credential_sig(v, issuer=blind.generate_issuer_key())
    tampered = format(int(good, 16) ^ 1, "x")
    for bad in (None, "", "zz", tampered, other_election, other_key, foreign_issuer):
        assert state.apply(_raw(v, bad), 500) == "invalid credential", bad
    missing = tx(v, "CAST_BALLOT", {"election_id": EID, "category": "profesor", "picks": ["A", "B", "C"]})
    assert state.apply(missing, 500) == "invalid credential"
    assert not state.elections[EID].ballots
    assert state.apply(_raw(v, good), 500) is None


def test_stolen_credential_cannot_be_used_by_another_key() -> None:
    state, _ = open_election()
    victim, thief = voter(), voter()
    assert state.apply(_raw(thief, credential_sig(victim)), 500) == "invalid credential"


def test_payload_has_no_personal_data() -> None:
    assert set(ballot(voter(), ["A", "B", "C"]).payload) == {"election_id", "category", "picks", "credential_sig"}
