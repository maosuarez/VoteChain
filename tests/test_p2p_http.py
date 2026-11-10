from dataclasses import asdict

import httpx
import pytest

from tests.net_helpers import Cluster, wait_until
from votechain.block import Block
from votechain.blockchain import Blockchain
from votechain.consensus import seal_block
from votechain.crypto import generate_keypair
from votechain.merkle import merkle_root
from votechain.p2p_http import parse_peers, runner_from_env
from votechain.store import ChainStoreError
from votechain.transactions import Transaction

KEY, PUB = generate_keypair()


def tx(n: int) -> Transaction:
    return Transaction.create("NOTE", {"n": n}, KEY, timestamp=n)


def post_tx(url: str, t: Transaction) -> None:
    assert httpx.post(url + "/p2p/tx", json={"src": None, "tx": t.to_dict()}).status_code == 202


@pytest.fixture
def cluster(tmp_path):
    c = Cluster(tmp_path)
    yield c
    c.shutdown()


def converged(c: Cluster, height: int) -> bool:
    return c.heights() == [height] * len(c.ids) and len(set(c.tips())) == 1


def test_three_validators_converge(cluster: Cluster) -> None:
    post_tx(cluster.url(0), tx(1))
    wait_until(lambda: converged(cluster, 2))
    block = httpx.get(cluster.url(2) + "/p2p/chain").json()[1]
    assert block["proposer"] == cluster.validators.proposer_for(1)  # v2 was on turn
    assert len(block["data"]["transactions"]) == 1


def test_non_validator_block_is_discarded(cluster: Cluster) -> None:
    outsider, _ = generate_keypair()
    genesis = cluster.runners["v1"].node.chain.chain[0]
    block = seal_block(1, 5, genesis.hash, {"transactions": []}, merkle_root([]), outsider)
    r = httpx.post(cluster.url(0) + "/p2p/block", json={"src": "x", "block": asdict(block)})
    assert r.status_code == 202
    post_tx(cluster.url(0), tx(1))  # processed after the bogus block (single worker queue)
    wait_until(lambda: converged(cluster, 2))
    assert all(b["proposer"] != block.proposer for b in httpx.get(cluster.url(0) + "/p2p/chain").json())


def test_down_peer_then_recovery_with_persisted_state(cluster: Cluster) -> None:
    cluster.stop(2)  # v3 owns block 2, not block 1
    post_tx(cluster.url(0), tx(1))
    wait_until(lambda: cluster.heights()[:2] == [2, 2])
    post_tx(cluster.url(0), tx(2))  # needs v3's turn: waits, no crash
    wait_until(lambda: cluster.runners["v1"].node.mempool.pending() != [])
    cluster.start(2)  # same port and data dir; rejoins and gets the pending tx rebroadcast
    wait_until(lambda: converged(cluster, 3), 20)
    assert cluster.runners["v3"].node.chain.chain[2].proposer == cluster.validators.proposer_for(2)


def test_restart_keeps_chain(cluster: Cluster) -> None:
    post_tx(cluster.url(0), tx(1))
    wait_until(lambda: converged(cluster, 2))
    before = list(cluster.runners["v1"].node.chain.chain)
    cluster.restart(0)
    assert cluster.runners["v1"].node.chain.chain == before  # loaded from disk before any sync


def test_garbage_message_does_not_kill_node(cluster: Cluster) -> None:
    for body in ({"src": "x", "block": {"nonsense": 1}}, {"src": "x", "block": {}}):
        httpx.post(cluster.url(0) + "/p2p/block", json=body)
    httpx.post(cluster.url(0) + "/p2p/tx", json={"src": "x", "tx": {"nonsense": 1}})
    post_tx(cluster.url(0), tx(1))
    wait_until(lambda: converged(cluster, 2))


def test_try_append_survives_malformed_block() -> None:
    chain = Blockchain()
    bad = Block.create(1, 1, chain.chain[0].hash, [], "x")  # data is not a dict, hash is consistent
    assert not chain.try_append(bad).valid
    assert len(chain.chain) == 1


def test_parse_peers() -> None:
    assert parse_peers("a=http://a:1, b=http://b:2") == {"a": "http://a:1", "b": "http://b:2"}
    with pytest.raises(ValueError):
        parse_peers("broken")


def test_runner_from_env_refuses_tampered_chain(tmp_path) -> None:
    c = Cluster(tmp_path / "c", 3)
    try:
        post_tx(c.url(0), tx(1))
        wait_until(lambda: converged(c, 2))
    finally:
        c.shutdown()
    path = tmp_path / "c" / "v1" / "chain.json"
    path.write_text(path.read_text().replace('"n": 1', '"n": 9'))
    env = {
        "VOTECHAIN_VALIDATORS": ",".join(c.validators.keys),
        "VOTECHAIN_NODE_ID": "v1",
        "VOTECHAIN_NODE_KEY": c.keys[0],
        "VOTECHAIN_DATA_DIR": str(tmp_path / "c" / "v1"),
    }
    with pytest.raises(ChainStoreError):
        runner_from_env(env, require_key=True)


def test_runner_from_env_rejects_foreign_key(tmp_path) -> None:
    other, _ = generate_keypair()
    env = {"VOTECHAIN_VALIDATORS": PUB, "VOTECHAIN_NODE_ID": "v1", "VOTECHAIN_NODE_KEY": other,
           "VOTECHAIN_DATA_DIR": str(tmp_path)}
    with pytest.raises(ValueError, match="does not belong"):
        runner_from_env(env, require_key=True)
