from votechain.consensus import ValidatorSet, seal_block
from votechain.crypto import generate_keypair
from votechain.merkle import merkle_root
from votechain.network import InMemoryTransport, Node
from votechain.transactions import Transaction
from dataclasses import asdict

KEYS = [generate_keypair() for _ in range(3)]
VALIDATORS = ValidatorSet(tuple(pub for _, pub in KEYS))
USER = generate_keypair()[0]


def make_net(extra: int = 0) -> tuple[InMemoryTransport, list[Node]]:
    t = InMemoryTransport()
    nodes = [Node(f"n{i}", t, VALIDATORS, priv) for i, (priv, _) in enumerate(KEYS)]
    return t, nodes


def tx(n: int) -> Transaction:
    return Transaction.create("t", {"n": n}, USER, timestamp=n)


def tips(nodes: list[Node]) -> set[str]:
    return {n.chain.chain[-1].hash for n in nodes}


def produce_round(nodes: list[Node]) -> None:
    """Whichever node is on turn (if reachable and present) produces."""
    for n in nodes:
        if n.produce_block():
            return


def test_transport_partition_blocks_messages() -> None:
    t, (n0, n1, n2) = make_net()
    t.partition({"n0", "n1"}, {"n2"})
    assert t.peers("n0") == ["n1"]
    n0.submit_tx(tx(1))
    assert len(n1.mempool) == 1 and len(n2.mempool) == 0


def test_tx_propagates_to_all_without_loops() -> None:
    _, nodes = make_net()
    assert nodes[0].submit_tx(tx(1))
    assert [len(n.mempool) for n in nodes] == [1, 1, 1]


def test_invalid_tx_dropped_not_forwarded() -> None:
    _, nodes = make_net()
    bad = {**tx(1).to_dict(), "payload": {"n": 2}}
    assert not nodes[0].receive_tx(bad, None)
    assert [len(n.mempool) for n in nodes] == [0, 0, 0]


def test_non_validator_does_not_produce() -> None:
    t = InMemoryTransport()
    outsider = Node("x", t, VALIDATORS, generate_keypair()[0])
    observer = Node("o", t, VALIDATORS)
    assert outsider.produce_block() is None
    assert observer.produce_block() is None


def test_out_of_turn_does_not_produce() -> None:
    _, (n0, n1, n2) = make_net()
    assert n0.produce_block() is None  # index 1 belongs to n1


def test_block_propagates_and_clears_mempools() -> None:
    _, (n0, n1, n2) = make_net()
    n0.submit_tx(tx(1))
    block = n1.produce_block()
    assert block is not None and len(block.data["transactions"]) == 1
    assert all(len(n.chain.chain) == 2 for n in (n0, n1, n2))
    assert all(len(n.mempool) == 0 for n in (n0, n1, n2))
    assert tips([n0, n1, n2]) == {block.hash}


def test_block_from_non_validator_rejected_and_not_forwarded() -> None:
    _, (n0, n1, n2) = make_net()
    priv = generate_keypair()[0]
    fake = seal_block(1, 1, n0.chain.chain[-1].hash, {"transactions": []}, merkle_root([]), priv)
    assert not n0.receive_block(asdict(fake), "x")
    assert all(len(n.chain.chain) == 1 for n in (n0, n1, n2))


def test_malformed_block_ignored() -> None:
    _, (n0, *_) = make_net()
    assert not n0.receive_block({"index": 1}, None)


def test_initial_sync() -> None:
    t, (n0, n1, n2) = make_net()
    t.partition({"n0", "n1"}, {"n2"})
    n1.produce_block()
    assert len(n2.chain.chain) == 1
    t.heal()
    assert n2.sync()
    assert n2.chain.chain == n1.chain.chain


def test_block_with_gap_triggers_sync() -> None:
    t, (n0, n1, n2) = make_net()
    t.partition({"n1", "n2"}, {"n0"})
    n1.produce_block()
    n2.produce_block()  # index 2
    t.heal()
    # n0 only sees block 2; it must pull the full chain from n2
    n0.receive_block(asdict(n2.chain.chain[2]), "n2")
    assert n0.chain.chain == n2.chain.chain


def test_three_nodes_converge_after_partition() -> None:
    t, nodes = make_net()
    n0, n1, n2 = nodes
    t.partition({"n1", "n2"}, {"n0"})
    n1.submit_tx(tx(1))
    assert n1.produce_block() is not None  # index 1
    assert n2.produce_block() is not None  # index 2
    assert n0.produce_block() is None  # index 1 not its turn; stuck at genesis
    assert [len(n.chain.chain) for n in nodes] == [1, 3, 3]
    t.heal()
    for n in nodes:
        n.sync()
    assert tips(nodes) == {n1.chain.chain[-1].hash}
    assert n0.produce_block() is not None  # index 3 is n0's turn
    assert tips(nodes) != set() and len(tips(nodes)) == 1
    assert all(n.chain.is_valid().valid and len(n.chain.chain) == 4 for n in nodes)


def test_unauthorized_node_cannot_get_block_accepted() -> None:
    t, nodes = make_net()
    outsider = Node("x", t, VALIDATORS, generate_keypair()[0])
    fake = seal_block(1, 1, outsider.chain.chain[-1].hash, {"transactions": []},
                      merkle_root([]), outsider.private_key or "")
    assert outsider.produce_block() is None
    for n in nodes:
        assert not n.receive_block(asdict(fake), "x")
    assert tips(nodes) == {nodes[0].chain.chain[0].hash}


def test_network_nodes_use_poa() -> None:
    _, nodes = make_net()
    assert all(n.chain.validators == VALIDATORS for n in nodes)
