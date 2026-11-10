import hashlib
import json
from dataclasses import dataclass, replace
from typing import Any


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Deterministic JSON: sorted keys, no spaces, UTF-8."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def meets_difficulty(block_hash: str, difficulty: int) -> bool:
    """True if the hash has at least `difficulty` leading zero bits."""
    return int(block_hash, 16) >> (256 - difficulty) == 0


@dataclass(frozen=True)
class Block:
    index: int
    timestamp: int
    prev_hash: str
    data: dict[str, Any]
    merkle_root: str
    nonce: int
    hash: str
    proposer: str = ""
    signature: str = ""  # signs `hash`; never part of it

    def compute_hash(self) -> str:
        """Single place deciding which fields enter the hash (excludes `hash`)."""
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "data": self.data,
            "merkle_root": self.merkle_root,
            "nonce": self.nonce,
            "proposer": self.proposer,
        }
        return hashlib.sha256(canonical_bytes(payload)).hexdigest()

    @classmethod
    def create(
        cls,
        index: int,
        timestamp: int,
        prev_hash: str,
        data: dict[str, Any],
        merkle_root: str,
        nonce: int = 0,
        proposer: str = "",
    ) -> "Block":
        unsigned = cls(
            index, timestamp, prev_hash, data, merkle_root, nonce, "", proposer
        )
        return replace(unsigned, hash=unsigned.compute_hash())

    @classmethod
    def mine(
        cls,
        index: int,
        timestamp: int,
        prev_hash: str,
        data: dict[str, Any],
        merkle_root: str,
        difficulty: int,
    ) -> tuple["Block", int]:
        """Search a nonce meeting `difficulty`; return (block, attempts)."""
        nonce = 0
        while True:
            block = cls.create(index, timestamp, prev_hash, data, merkle_root, nonce)
            if meets_difficulty(block.hash, difficulty):
                return block, nonce + 1
            nonce += 1
