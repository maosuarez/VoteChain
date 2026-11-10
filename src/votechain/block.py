import hashlib
import json
from dataclasses import dataclass
from typing import Any


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    """Deterministic JSON: sorted keys, no spaces, UTF-8."""
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


@dataclass(frozen=True)
class Block:
    index: int
    timestamp: int
    prev_hash: str
    data: dict[str, Any]
    hash: str

    def compute_hash(self) -> str:
        """Single place deciding which fields enter the hash (excludes `hash`)."""
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "data": self.data,
        }
        return hashlib.sha256(canonical_bytes(payload)).hexdigest()

    @classmethod
    def create(
        cls, index: int, timestamp: int, prev_hash: str, data: dict[str, Any]
    ) -> "Block":
        unsigned = cls(index, timestamp, prev_hash, data, hash="")
        return cls(index, timestamp, prev_hash, data, unsigned.compute_hash())
