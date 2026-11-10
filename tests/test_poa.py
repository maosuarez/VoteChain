from dataclasses import replace

import pytest

from votechain.block import Block
from votechain.blockchain import Blockchain
from votechain.consensus import ValidatorSet, seal_block
from votechain.crypto import generate_keypair
from votechain.merkle import merkle_root

EMPTY = {"transactions": []}
KEYS = [generate_keypair() for _ in range(3)]  # (priv, pub)
VALIDATORS = ValidatorSet(tuple(pub for _, pub in KEYS))


def seal(chain: Blockchain, priv: str, data: dict = EMPTY, ts: int = 1) -> Block:
    return seal_block(
        len(chain.chain), ts, chain.chain[-1].hash, data,
        merkle_root(data["transactions"]), priv,
    )


def next_priv(chain: Blockchain) -> str:
    pub = VALIDATORS.proposer_for(len(chain.chain))
    return next(priv for priv, p in KEYS if p == pub)


def test_validator_set_valid_keeps_order() -> None:
    assert ValidatorSet(tuple(p for _, p in KEYS)).keys == tuple(p for _, p in KEYS)


def test_validator_set_rejects_empty_and_duplicates() -> None:
    with pytest.raises(ValueError):
        ValidatorSet(())
    with pytest.raises(ValueError):
        ValidatorSet((KEYS[0][1], KEYS[0][1]))


def test_round_robin_rotation() -> None:
    v = [p for _, p in KEYS]
    assert [VALIDATORS.proposer_for(i) for i in (1, 2, 3, 4)] == [v[1], v[2], v[0], v[1]]


def test_block_by_validator_on_turn_is_valid() -> None:
    bc = Blockchain(validators=VALIDATORS)
    assert bc.try_append(seal(bc, next_priv(bc))).valid
    assert bc.try_append(seal(bc, next_priv(bc), ts=2)).valid
    assert bc.is_valid().valid


def test_tampered_signature_rejected() -> None:
    bc = Blockchain(validators=VALIDATORS)
    b = seal(bc, next_priv(bc))
    bad = replace(b, signature=("0" if b.signature[0] != "0" else "1") + b.signature[1:])
    r = bc.try_append(bad)
    assert (r.valid, r.bad_index, r.reason) == (False, 1, "invalid block signature")
    assert len(bc.chain) == 1


def test_unauthorized_proposer_rejected() -> None:
    bc = Blockchain(validators=VALIDATORS)
    r = bc.try_append(seal(bc, generate_keypair()[0]))
    assert (r.valid, r.reason) == (False, "unauthorized proposer")
    assert len(bc.chain) == 1


def test_validator_out_of_turn_rejected() -> None:
    bc = Blockchain(validators=VALIDATORS)
    wrong = next(priv for priv, p in KEYS if p != VALIDATORS.proposer_for(1))
    r = bc.try_append(seal(bc, wrong))
    assert (r.valid, r.reason) == (False, "proposer out of turn")


def test_swapped_proposer_rejected() -> None:
    bc = Blockchain(validators=VALIDATORS)
    b = seal(bc, generate_keypair()[0])
    forged = Block.create(
        b.index, b.timestamp, b.prev_hash, b.data, b.merkle_root,
        proposer=VALIDATORS.proposer_for(1),
    )
    forged = replace(forged, signature=b.signature)
    assert not bc.try_append(forged).valid


def test_poa_does_not_require_work() -> None:
    bc = Blockchain(difficulty=40, validators=VALIDATORS)  # unreachable PoW
    assert bc.try_append(seal(bc, next_priv(bc))).valid


def test_proposer_in_hash_signature_not() -> None:
    bc = Blockchain(validators=VALIDATORS)
    b = seal(bc, next_priv(bc))
    assert replace(b, signature="junk").compute_hash() == b.hash
    assert replace(b, proposer=KEYS[0][1]).compute_hash() != b.hash


def test_replace_chain_longer_valid_wins() -> None:
    a, b = Blockchain(validators=VALIDATORS), Blockchain(validators=VALIDATORS)
    for ts in (1, 2):
        b.try_append(seal(b, next_priv(b), ts=ts))
    assert a.replace_chain(b.chain)
    assert a.chain == b.chain


def test_replace_chain_invalid_longer_rejected() -> None:
    a, b = Blockchain(validators=VALIDATORS), Blockchain(validators=VALIDATORS)
    for ts in (1, 2):
        b.try_append(seal(b, next_priv(b), ts=ts))
    b.chain[1] = replace(b.chain[1], signature="00" * 64)
    assert not a.replace_chain(b.chain)
    assert len(a.chain) == 1


def test_replace_chain_tie_is_deterministic() -> None:
    # equivocation: same validator signs two different blocks at index 1
    a, b = Blockchain(validators=VALIDATORS), Blockchain(validators=VALIDATORS)
    a.try_append(seal(a, next_priv(a), ts=1))
    b.try_append(seal(b, next_priv(b), ts=2))
    assert a.chain[1].hash != b.chain[1].hash
    a_before, b_before = list(a.chain), list(b.chain)
    a.replace_chain(b_before)
    b.replace_chain(a_before)
    assert a.chain == b.chain
    assert a.chain[-1].hash == min(a_before[-1].hash, b_before[-1].hash)
