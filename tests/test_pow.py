from dataclasses import replace
from statistics import mean

from votechain.block import Block, meets_difficulty
from votechain.blockchain import Blockchain
from votechain.crypto import generate_keypair
from votechain.mempool import Mempool
from votechain.merkle import merkle_root
from votechain.transactions import Transaction

EMPTY = {"transactions": []}


def tx_dict(n: int, priv: str | None = None) -> dict:
    priv = priv or generate_keypair()[0]
    return Transaction.create("t", {"n": n}, priv, timestamp=n).to_dict()


def test_mined_block_meets_difficulty() -> None:
    bc = Blockchain(difficulty=10)
    block, attempts = bc.mine_block(EMPTY, timestamp=1)
    assert meets_difficulty(block.hash, 10)
    assert block.hash == block.compute_hash()
    assert attempts == block.nonce + 1
    assert bc.is_valid().valid


def test_difficulty_zero_accepts_first_nonce() -> None:
    block, attempts = Blockchain(difficulty=0).mine_block(EMPTY, timestamp=1)
    assert (block.nonce, attempts) == (0, 1)


def test_attempts_grow_with_difficulty() -> None:
    def avg(d: int) -> float:
        return mean(
            Block.mine(1, t, "0" * 64, EMPTY, merkle_root([]), d)[1] for t in range(40)
        )

    assert avg(0) < avg(4) < avg(8)


def test_block_without_work_rejected() -> None:
    bc = Blockchain(difficulty=16)
    bc.add_block(EMPTY, timestamp=1)
    # valid hash, but unmined: find a nonce that does NOT meet difficulty
    prev = bc.chain[-1]
    block = Block.create(2, 2, prev.hash, EMPTY, merkle_root([]), 0)
    assert not meets_difficulty(block.hash, 16)
    bc.chain.append(block)
    r = bc.is_valid()
    assert (r.valid, r.bad_index) == (False, 2)


def test_nonce_altered_rejected() -> None:
    bc = Blockchain(difficulty=12)
    bc.add_block(EMPTY, timestamp=1)
    bc.chain[1] = replace(bc.chain[1], nonce=bc.chain[1].nonce + 1)
    r = bc.is_valid()
    assert (r.valid, r.bad_index) == (False, 1)


def test_tampered_tx_with_merkle_and_hash_recomputed() -> None:
    bc = Blockchain()
    bc.add_block({"transactions": [tx_dict(1)]}, timestamp=1)
    b = bc.chain[1]
    forged = {**b.data["transactions"][0], "payload": {"n": 999}}
    data = {"transactions": [forged]}
    bc.chain[1] = Block.create(1, b.timestamp, b.prev_hash, data, merkle_root([forged]))
    r = bc.is_valid()
    assert (r.valid, r.bad_index) == (False, 1)
    assert "signature" in r.reason


def test_inconsistent_merkle_root() -> None:
    bc = Blockchain()
    bc.add_block({"transactions": [tx_dict(1)]}, timestamp=1)
    b = bc.chain[1]
    bc.chain[1] = Block.create(1, b.timestamp, b.prev_hash, b.data, merkle_root([]))
    r = bc.is_valid()
    assert (r.valid, r.bad_index) == (False, 1)
    assert "merkle" in r.reason


def test_tx_reinclusion_rejected() -> None:
    bc = Blockchain()
    tx = tx_dict(1)
    bc.add_block({"transactions": [tx]}, timestamp=1)
    bc.add_block({"transactions": [tx]}, timestamp=2)
    r = bc.is_valid()
    assert (r.valid, r.bad_index) == (False, 2)


def test_malformed_transaction_rejected() -> None:
    bc = Blockchain()
    bc.add_block({"transactions": [{"type": "x"}]}, timestamp=1)
    assert not bc.is_valid().valid


def test_end_to_end_sign_mempool_mine() -> None:
    bc, pool = Blockchain(difficulty=8), Mempool()
    priv, pub = generate_keypair()
    txs = [Transaction.create("t", {"n": n}, priv, timestamp=n) for n in range(3)]
    for tx in txs:
        assert pool.add(tx)[0]
    block = bc.add_block_from_mempool(pool, max_txs=2, timestamp=10)
    assert block.data["transactions"] == [t.to_dict() for t in txs[:2]]
    assert len(pool) == 1
    bc.add_block_from_mempool(pool, max_txs=2, timestamp=11)
    assert len(pool) == 0
    assert bc.is_valid().valid
    assert block.data["transactions"][0]["sender"] == pub


def test_mempool_tx_already_on_chain_skipped() -> None:
    bc, pool = Blockchain(), Mempool()
    tx = Transaction.create("t", {}, generate_keypair()[0], timestamp=1)
    pool.add(tx)
    bc.add_block_from_mempool(pool, 5, timestamp=1)
    pool.add(tx)
    bc.add_block_from_mempool(pool, 5, timestamp=2)
    assert bc.chain[2].data["transactions"] == []
    assert bc.is_valid().valid
