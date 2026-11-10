from votechain.blockchain import Blockchain
from votechain.crypto import generate_keypair
from votechain.voting import build_state
from tests.voting_helpers import EID, ISSUER, ballot, open_election, tx


def entries(state):
    return {e.candidate_id: e for e in state.tally(EID)["profesor"]}


def test_sum_of_points() -> None:
    state, _ = open_election()
    state.apply(ballot(generate_keypair()[0], ["A", "B", "C"]), 5)
    state.apply(ballot(generate_keypair()[0], ["B", "A", "C"]), 5)
    e = entries(state)
    assert (e["A"].points, e["B"].points, e["C"].points, e["D"].points) == (5, 5, 2, 0)


def cast(state, picks) -> None:
    assert state.apply(ballot(generate_keypair()[0], picks), 5) is None


def test_tiebreak_by_firsts() -> None:
    state, _ = open_election()
    cast(state, ["A", "B", "D"])  # A3 B2 D1
    cast(state, ["C", "B", "A"])  # C3 B2 A1
    e = entries(state)
    assert e["A"].points == e["B"].points == 4
    assert e["A"].rank == 1 and e["B"].rank == 2 and not e["A"].tied


def test_tiebreak_by_seconds() -> None:
    state, _ = open_election()
    for picks in (["A", "C", "D"], ["B", "D", "C"], ["C", "B", "D"], ["D", "C", "A"], ["C", "D", "A"]):
        cast(state, picks)
    e = entries(state)
    assert e["A"].points == e["B"].points == 5
    assert e["A"].firsts == e["B"].firsts == 1
    assert e["B"].rank < e["A"].rank and not e["A"].tied


def test_declared_tie() -> None:
    state, _ = open_election()
    cast(state, ["A", "B", "C"])
    cast(state, ["B", "A", "C"])
    e = entries(state)
    assert e["A"].rank == e["B"].rank == 1 and e["A"].tied and e["B"].tied
    assert not e["C"].tied and e["C"].rank == 3


def test_replay_from_real_chain_ignores_invalid() -> None:
    admin = generate_keypair()[0]
    v1, v2 = generate_keypair()[0], generate_keypair()[0]
    chain = Blockchain()
    txs = [tx(admin, "CREATE_ELECTION", {"election_id": EID, "opens_at": 0, "closes_at": 1000, "issuer_key": ISSUER.public()})]
    txs.append(tx(admin, "ADD_CATEGORY", {"election_id": EID, "category": "profesor"}))
    for c in "ABC":
        txs.append(tx(admin, "ADD_CANDIDATE", {"election_id": EID, "category": "profesor", "candidate_id": c, "name": c}))
    txs.append(tx(admin, "OPEN_ELECTION", {"election_id": EID}))
    txs.append(ballot(v1, ["A", "B", "C"]))
    txs.append(ballot(v1, ["C", "B", "A"]))  # doble voto
    txs.append(ballot(v2, ["A", "A", "B"]))  # inválida
    txs.append(ballot(v2, ["B", "A", "C"]))
    chain.add_block({"transactions": [t.to_dict() for t in txs]}, timestamp=500)
    assert chain.is_valid().valid
    first, second = build_state(chain).tally(EID), build_state(chain).tally(EID)
    assert first == second
    pts = {e.candidate_id: e.points for e in first["profesor"]}
    assert pts == {"A": 5, "B": 5, "C": 2}


def test_partial_tally_while_open() -> None:
    state, _ = open_election()
    assert all(e.points == 0 for e in state.tally(EID)["profesor"])
