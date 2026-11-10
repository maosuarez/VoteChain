import copy
import shutil
from dataclasses import asdict

import pytest

from tests.voting_helpers import EID, ISSUER, ballot, tx
from votechain.audit import audit_chains
from votechain.blockchain import Blockchain
from votechain.consensus import ValidatorSet, seal_block
from votechain.crypto import generate_keypair, public_key_hex
from votechain.merkle import merkle_root

VALIDATOR_KEYS = [generate_keypair()[0] for _ in range(3)]
TRUSTED = ValidatorSet(tuple(public_key_hex(k) for k in VALIDATOR_KEYS))
ADMIN, _ = generate_keypair()


def build_poa_chain() -> list[dict]:
    """PoA chain with a closed election: 3 voters, picks A>B>C, A>C>B, B>A>C."""
    chain = Blockchain(validators=TRUSTED)
    voters = [generate_keypair()[0] for _ in range(3)]
    steps = [
        [tx(ADMIN, "CREATE_ELECTION", {"election_id": EID, "opens_at": 0, "closes_at": 10**10,
                                       "issuer_key": ISSUER.public()})],
        [tx(ADMIN, "ADD_CATEGORY", {"election_id": EID, "category": "profesor"})],
        [tx(ADMIN, "ADD_CANDIDATE", {"election_id": EID, "category": "profesor", "candidate_id": c, "name": c})
         for c in "ABCD"],
        [tx(ADMIN, "OPEN_ELECTION", {"election_id": EID})],
        [ballot(voters[0], ["A", "B", "C"]), ballot(voters[1], ["A", "C", "B"])],
        [ballot(voters[2], ["B", "A", "C"])],
        [tx(ADMIN, "CLOSE_ELECTION", {"election_id": EID})],
    ]
    for txs in steps:
        index = len(chain.chain)
        data = {"transactions": [t.to_dict() for t in txs]}
        key = VALIDATOR_KEYS[index % 3]
        block = seal_block(index, 100 + index, chain.chain[-1].hash, data, merkle_root(data["transactions"]), key)
        assert chain.try_append(block).valid
    return [asdict(b) for b in chain.chain]


@pytest.fixture(scope="module")
def good() -> list[dict]:
    return build_poa_chain()


def points(report) -> dict[str, int]:
    return {e["candidate_id"]: e["points"] for e in report.tally["profesor"]}


def test_consistent_nodes_pass_and_recount(good) -> None:
    report = audit_chains({"v1": good, "v2": copy.deepcopy(good)}, TRUSTED, EID)
    assert report.ok, report.findings
    assert points(report) == {"A": 8, "B": 6, "C": 4, "D": 0}  # A 3+3+2, B 2+1+3, C 1+2+1


def test_tampered_ballot_names_node_and_block(good) -> None:
    bad = copy.deepcopy(good)
    block = next(i for i, b in enumerate(bad) if len(b["data"]["transactions"]) == 2)
    bad[block]["data"]["transactions"][0]["payload"]["picks"] = ["D", "C", "B"]
    report = audit_chains({"v1": good, "v2": bad}, TRUSTED, EID)
    assert not report.ok
    assert any(f.startswith("v2: invalid at block %d" % block) for f in report.findings)


def test_untrusted_validator_set_fails(good) -> None:
    other = ValidatorSet(tuple(generate_keypair()[1] for _ in range(3)))
    report = audit_chains({"v1": good}, other, EID)
    assert not report.ok and "unauthorized proposer" in report.findings[0]


def test_nodes_with_different_height_are_reported(good) -> None:
    report = audit_chains({"v1": good, "v2": good[:-1]}, TRUSTED, EID)
    assert any("v2 differs from v1" in f for f in report.findings)


def test_published_tally_mismatch_detected(good) -> None:
    honest = audit_chains({"v1": good}, TRUSTED, EID).tally
    forged = copy.deepcopy(honest)
    forged["profesor"][0]["points"] += 1
    assert audit_chains({"v1": good}, TRUSTED, EID, published_tally=honest).ok
    assert not audit_chains({"v1": good}, TRUSTED, EID, published_tally=forged).ok


def test_unknown_election(good) -> None:
    assert not audit_chains({"v1": good}, TRUSTED, "nope").ok


def test_malformed_data_is_a_finding_not_a_crash() -> None:
    report = audit_chains({"v1": [{"nonsense": 1}]}, TRUSTED, EID)
    assert report.findings == ["v1: malformed chain data", "no node served a valid chain"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed; explorer check not executed")
def test_explorer_verifier_agrees_with_python_recount(good) -> None:
    report = audit_chains({"v1": good}, TRUSTED, EID, use_explorer=True)
    assert report.ok, report.findings
    assert report.explorer == "ok"


def test_explorer_reports_skip_without_node(good, monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    report = audit_chains({"v1": good}, TRUSTED, EID, use_explorer=True)
    assert report.ok and report.explorer.startswith("skipped")
