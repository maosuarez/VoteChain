from votechain.crypto import generate_keypair
from votechain.voting import CLOSED, DRAFT, OPEN, VotingState
from tests.voting_helpers import EID, ISSUER, draft_election, open_election, tx


def test_create_and_structure() -> None:
    admin = generate_keypair()[0]
    state = VotingState()
    draft_election(state, admin)
    e = state.elections[EID]
    assert e.status == DRAFT and len(e.candidates["profesor"]) == 4


def test_duplicate_election_and_bad_window() -> None:
    admin = generate_keypair()[0]
    state = VotingState()
    p = {"election_id": EID, "opens_at": 0, "closes_at": 10, "issuer_key": ISSUER.public()}
    assert state.apply(tx(admin, "CREATE_ELECTION", p), 1) is None
    assert state.apply(tx(admin, "CREATE_ELECTION", {**p, "closes_at": 99}), 1)
    assert state.elections[EID].closes_at == 10
    assert state.apply(tx(admin, "CREATE_ELECTION", {**p, "election_id": "x", "opens_at": 10}), 1)


def test_non_admin_rejected() -> None:
    admin, other = generate_keypair()[0], generate_keypair()[0]
    state = VotingState()
    draft_election(state, admin)
    assert state.apply(tx(other, "ADD_CATEGORY", {"election_id": EID, "category": "x"}), 1)
    assert state.apply(tx(other, "ADD_CANDIDATE", {"election_id": EID, "category": "profesor", "candidate_id": "Z", "name": "Z"}), 1)
    assert state.apply(tx(other, "OPEN_ELECTION", {"election_id": EID}), 1)
    assert state.elections[EID].status == DRAFT


def test_duplicates_rejected() -> None:
    admin = generate_keypair()[0]
    state = VotingState()
    draft_election(state, admin)
    assert state.apply(tx(admin, "ADD_CATEGORY", {"election_id": EID, "category": "profesor"}), 1)
    assert state.apply(tx(admin, "ADD_CANDIDATE", {"election_id": EID, "category": "profesor", "candidate_id": "A", "name": "A"}), 1)


def test_open_requires_three_candidates() -> None:
    admin = generate_keypair()[0]
    state = VotingState()
    assert state.apply(tx(admin, "CREATE_ELECTION", {"election_id": EID, "opens_at": 0, "closes_at": 9, "issuer_key": ISSUER.public()}), 1) is None
    assert state.apply(tx(admin, "OPEN_ELECTION", {"election_id": EID}), 1)  # no categories
    state.apply(tx(admin, "ADD_CATEGORY", {"election_id": EID, "category": "c"}), 1)
    for c in "AB":
        state.apply(tx(admin, "ADD_CANDIDATE", {"election_id": EID, "category": "c", "candidate_id": c, "name": c}), 1)
    assert state.apply(tx(admin, "OPEN_ELECTION", {"election_id": EID}), 1)


def test_no_changes_after_open() -> None:
    state, admin = open_election()
    assert state.apply(tx(admin, "ADD_CATEGORY", {"election_id": EID, "category": "n"}), 1)
    assert state.apply(tx(admin, "ADD_CANDIDATE", {"election_id": EID, "category": "profesor", "candidate_id": "Z", "name": "Z"}), 1)
    assert state.elections[EID].status == OPEN


def test_close_is_final() -> None:
    state, admin = open_election()
    other = generate_keypair()[0]
    assert state.apply(tx(other, "CLOSE_ELECTION", {"election_id": EID}), 1)
    assert state.apply(tx(admin, "CLOSE_ELECTION", {"election_id": EID}), 1) is None
    assert state.elections[EID].status == CLOSED
    assert state.apply(tx(admin, "OPEN_ELECTION", {"election_id": EID}), 1)
    assert state.apply(tx(admin, "CLOSE_ELECTION", {"election_id": EID}), 1)


def test_invalid_issuer_key_rejected() -> None:
    admin = generate_keypair()[0]
    state = VotingState()
    p = {"election_id": EID, "opens_at": 0, "closes_at": 10}
    for bad in (None, {}, {"n": "zz", "e": 65537}, {"n": "ff", "e": 65537}, {"n": ISSUER.public()["n"], "e": 4}):
        assert state.apply(tx(admin, "CREATE_ELECTION", {**p, "issuer_key": bad}), 1), bad
    assert state.apply(tx(admin, "CREATE_ELECTION", p), 1)  # missing key
    assert EID not in state.elections


def test_issuer_key_recorded() -> None:
    state, _ = open_election()
    assert state.elections[EID].issuer_key == ISSUER.public()
