import json
import shutil
import subprocess
from dataclasses import asdict
from pathlib import Path

import pytest

from tests.make_vectors import CANONICAL_INPUTS, VECTORS, _txs
from votechain.block import Block, canonical_bytes
from votechain.blockchain import Blockchain
from votechain.merkle import merkle_proof, merkle_root
from votechain.transactions import Transaction
from votechain.voting import build_state

ROOT = Path(__file__).resolve().parents[1]
vec = json.loads(VECTORS.read_text(encoding="utf-8"))


def test_vectors_match_backend() -> None:
    """Stored vectors still equal what the backend computes (detects backend drift)."""
    for c in vec["canonical"]:
        assert canonical_bytes(c["input"]).decode() == c["output"]
    for m in vec["merkle"]:
        assert merkle_root(m["txs"]) == m["root"]
        assert [merkle_proof(m["txs"], i) for i in range(len(m["txs"]))] == m["proofs"]
    assert [c["input"] for c in vec["canonical"]] == CANONICAL_INPUTS
    assert [m["txs"] for m in vec["merkle"]] == [_txs(n) for n in (0, 1, 2, 3, 5)]
    for b in vec["block_hash"]:
        assert Block(**b["block"]).compute_hash() == b["hash"]

    chain = Blockchain()
    chain.chain = [Block(**b) for b in vec["chain"]]
    assert chain.is_valid().valid
    state = build_state(chain)
    tally = {c: [asdict(e) for e in es] for c, es in state.tally(vec["election_id"]).items()}
    assert tally == vec["tally"]
    ids = {Transaction.from_dict(t).tx_id for b in chain.chain for t in b.data["transactions"]}
    assert all(r["tx_id"] in ids for r in vec["receipts"])


def test_browser_logic_parity_with_node() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed; JS parity not executed")
    result = subprocess.run(
        [node, str(ROOT / "tests/js/parity.test.js")], capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
