import hashlib
from typing import Any

from votechain.block import canonical_bytes

LEAF_PREFIX = b"\x00"
NODE_PREFIX = b"\x01"


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def merkle_root(tx_dicts: list[dict[str, Any]]) -> str:
    """Domain-separated Merkle root; an odd last node is promoted, not duplicated."""
    if not tx_dicts:
        return _sha256(b"").hex()
    level = [_sha256(LEAF_PREFIX + canonical_bytes(tx)) for tx in tx_dicts]
    while len(level) > 1:
        nxt = [
            _sha256(NODE_PREFIX + level[i] + level[i + 1])
            for i in range(0, len(level) - 1, 2)
        ]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
    return level[0].hex()


def merkle_proof(tx_dicts: list[dict[str, Any]], index: int) -> list[dict[str, str]]:
    """Inclusion proof for leaf `index`: sibling hashes bottom-up, each with its side.

    A promoted odd node has no sibling at that level, so it adds no step.
    """
    level = [_sha256(LEAF_PREFIX + canonical_bytes(tx)) for tx in tx_dicts]
    proof: list[dict[str, str]] = []
    while len(level) > 1:
        sibling = index ^ 1
        if sibling < len(level):
            proof.append({"side": "left" if sibling < index else "right", "hash": level[sibling].hex()})
        nxt = [
            _sha256(NODE_PREFIX + level[i] + level[i + 1])
            for i in range(0, len(level) - 1, 2)
        ]
        if len(level) % 2:
            nxt.append(level[-1])
        level = nxt
        index //= 2
    return proof
