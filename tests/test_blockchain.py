from dataclasses import replace

from votechain.block import Block, canonical_bytes
from votechain.blockchain import GENESIS_BLOCK, Blockchain
from votechain.merkle import merkle_root

EMPTY = {"transactions": []}
ROOT = merkle_root([])


def blk(index: int, ts: int, prev: str, data: dict) -> Block:
    return Block.create(index, ts, prev, data, merkle_root(data["transactions"]))


def make_chain() -> Blockchain:
    bc = Blockchain()
    for n in range(1, 4):
        bc.add_block({"transactions": [], "n": n}, timestamp=n)
    return bc


# Block
def test_hash_deterministic() -> None:
    a = Block.create(1, 5, "0" * 64, {"x": 1}, ROOT)
    b = Block.create(1, 5, "0" * 64, {"x": 1}, ROOT)
    assert a.hash == b.hash


def test_stored_hash_not_part_of_computation() -> None:
    a = Block.create(1, 5, "0" * 64, {"x": 1}, ROOT)
    assert replace(a, hash="junk").compute_hash() == a.hash


def test_minimal_change_changes_hash() -> None:
    a = Block.create(1, 5, "0" * 64, {"x": 1}, ROOT)
    assert replace(a, data={"x": 2}).compute_hash() != a.hash


def test_merkle_root_change_changes_hash() -> None:
    a = Block.create(1, 5, "0" * 64, {"x": 1}, ROOT)
    assert replace(a, merkle_root="ab" * 32).compute_hash() != a.hash


def test_nonce_change_changes_hash() -> None:
    a = Block.create(1, 5, "0" * 64, {"x": 1}, ROOT)
    assert replace(a, nonce=1).compute_hash() != a.hash


def test_key_order_irrelevant() -> None:
    assert canonical_bytes({"a": 1, "b": 2}) == canonical_bytes({"b": 2, "a": 1})


def test_fixed_vector() -> None:
    block = Block.create(1, 1700000000, "0" * 64, {"voto": "ñ", "n": 1}, ROOT, 7)
    assert block.hash == FIXED_HASH


# Blockchain
def test_genesis_identical_between_instances() -> None:
    a, b = Blockchain(), Blockchain()
    assert a.chain[0].hash == b.chain[0].hash
    assert a.chain[0].prev_hash == "0" * 64


def test_new_chain_valid() -> None:
    assert Blockchain().is_valid().valid


def test_add_block_links() -> None:
    bc = make_chain()
    assert [b.index for b in bc.chain] == [0, 1, 2, 3]
    assert bc.chain[2].prev_hash == bc.chain[1].hash
    assert bc.is_valid().valid


def test_tampered_data_detected() -> None:
    bc = make_chain()
    bc.chain[2] = replace(bc.chain[2], data={"transactions": [], "n": 99})
    r = bc.is_valid()
    assert (r.valid, r.bad_index) == (False, 2)


def test_tampered_data_with_rehash_fails_next() -> None:
    bc = make_chain()
    b = bc.chain[2]
    bc.chain[2] = blk(b.index, b.timestamp, b.prev_hash, {"transactions": [], "n": 99})
    r = bc.is_valid()
    assert (r.valid, r.bad_index) == (False, 3)


def test_non_consecutive_index() -> None:
    bc = make_chain()
    b = bc.chain[2]
    bc.chain[2] = blk(7, b.timestamp, b.prev_hash, b.data)
    r = bc.is_valid()
    assert (r.valid, r.bad_index) == (False, 2)


def test_genesis_tampered() -> None:
    bc = make_chain()
    bc.chain[0] = blk(0, 0, "0" * 64, {"transactions": [], "genesis": False})
    r = bc.is_valid()
    assert (r.valid, r.bad_index) == (False, 0)


def test_intermediate_block_removed() -> None:
    bc = make_chain()
    del bc.chain[2]
    assert not bc.is_valid().valid


def test_genesis_constant() -> None:
    assert Blockchain().chain[0] is GENESIS_BLOCK


FIXED_HASH = "7dcc32944e9033d22d6721cd48997861e3a08bc8d6bde59fb40ed753df4bf380"


def test_proposer_changes_hash_signature_does_not() -> None:
    a = Block.create(1, 5, "0" * 64, {"x": 1}, ROOT)
    assert Block.create(1, 5, "0" * 64, {"x": 1}, ROOT, proposer="ab" * 32).hash != a.hash
    assert replace(a, signature="junk").compute_hash() == a.hash
