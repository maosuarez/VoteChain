from votechain.merkle import merkle_root

A, B, C = {"a": 1}, {"b": 2}, {"c": 3}


def test_deterministic() -> None:
    assert merkle_root([A, B, C]) == merkle_root([A, B, C])


def test_order_matters() -> None:
    assert merkle_root([A, B]) != merkle_root([B, A])


def test_odd_list_no_collision() -> None:
    assert merkle_root([A, B, C]) != merkle_root([A, B, C, C])


def test_empty_constant() -> None:
    assert merkle_root([]) == merkle_root([])
    assert len(merkle_root([])) == 64


def test_single_differs_from_empty() -> None:
    assert merkle_root([A]) != merkle_root([])


def _verify(tx: dict, proof: list[dict[str, str]]) -> str:
    import hashlib

    from votechain.block import canonical_bytes
    from votechain.merkle import LEAF_PREFIX, NODE_PREFIX

    node = hashlib.sha256(LEAF_PREFIX + canonical_bytes(tx)).digest()
    for step in proof:
        sib = bytes.fromhex(step["hash"])
        pair = sib + node if step["side"] == "left" else node + sib
        node = hashlib.sha256(NODE_PREFIX + pair).digest()
    return node.hex()


def test_proof_rebuilds_root_for_every_leaf() -> None:
    from votechain.merkle import merkle_proof

    for n in (1, 2, 3, 5, 8):
        txs = [{"i": i} for i in range(n)]
        for i, tx in enumerate(txs):
            assert _verify(tx, merkle_proof(txs, i)) == merkle_root(txs)


def test_proof_of_other_leaf_fails() -> None:
    from votechain.merkle import merkle_proof

    txs = [{"i": i} for i in range(3)]
    assert _verify({"i": 9}, merkle_proof(txs, 0)) != merkle_root(txs)
