from dataclasses import replace

from votechain.crypto import generate_keypair, sign
from votechain.block import canonical_bytes
from votechain.mempool import Mempool
from votechain.transactions import Transaction


def make_tx(n: int = 1, key: str | None = None) -> Transaction:
    priv = key or generate_keypair()[0]
    return Transaction.create("test", {"n": n}, priv, timestamp=100 + n)


def test_valid_transaction() -> None:
    assert make_tx().verify()


def test_altered_fields_fail() -> None:
    tx = make_tx()
    assert not replace(tx, payload={"n": 2}).verify()
    assert not replace(tx, type="other").verify()
    assert not replace(tx, timestamp=1).verify()
    assert not replace(tx, sender=generate_keypair()[1]).verify()


def test_signature_from_other_identity() -> None:
    other_priv, _ = generate_keypair()
    victim_pub = generate_keypair()[1]
    tx = make_tx()
    forged = replace(tx, sender=victim_pub)
    forged = replace(forged, signature=sign(other_priv, canonical_bytes(forged.body())))
    assert not forged.verify()


def test_malformed_signature_or_sender_no_exception() -> None:
    tx = make_tx()
    assert not replace(tx, signature="nothex").verify()
    assert not replace(tx, signature="").verify()
    assert not replace(tx, sender="nothex").verify()


def test_tx_id_deterministic_and_excludes_signature() -> None:
    tx = make_tx()
    assert tx.tx_id == replace(tx, signature="").tx_id
    assert tx.tx_id != replace(tx, payload={"n": 9}).tx_id


def test_dict_roundtrip() -> None:
    tx = make_tx()
    assert Transaction.from_dict(tx.to_dict()) == tx


# Mempool
def test_mempool_rejects_invalid_signature() -> None:
    pool = Mempool()
    ok, _ = pool.add(replace(make_tx(), payload={"n": 2}))
    assert not ok and len(pool) == 0


def test_mempool_rejects_duplicate() -> None:
    pool, tx = Mempool(), make_tx()
    assert pool.add(tx)[0]
    assert not pool.add(tx)[0]
    assert len(pool) == 1


def test_mempool_arrival_order_and_max() -> None:
    pool = Mempool()
    txs = [make_tx(n) for n in range(5)]
    for tx in txs:
        pool.add(tx)
    assert pool.pop_batch(3) == txs[:3]
    assert len(pool) == 2
    assert pool.pop_batch(10) == txs[3:]
    assert len(pool) == 0
