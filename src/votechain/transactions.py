import hashlib
import time
from dataclasses import dataclass
from typing import Any

from votechain.block import canonical_bytes
from votechain.crypto import public_key_hex, sign, verify


@dataclass(frozen=True)
class Transaction:
    type: str
    payload: dict[str, Any]
    sender: str
    timestamp: int
    signature: str

    def body(self) -> dict[str, Any]:
        """Signed content: every field except the signature."""
        return {
            "type": self.type,
            "payload": self.payload,
            "sender": self.sender,
            "timestamp": self.timestamp,
        }

    @property
    def tx_id(self) -> str:
        return hashlib.sha256(canonical_bytes(self.body())).hexdigest()

    def verify(self) -> bool:
        return verify(self.sender, self.signature, canonical_bytes(self.body()))

    def to_dict(self) -> dict[str, Any]:
        return {**self.body(), "signature": self.signature}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Transaction":
        """Raises KeyError/TypeError on malformed input."""
        return cls(d["type"], d["payload"], d["sender"], d["timestamp"], d["signature"])

    @classmethod
    def create(
        cls,
        type: str,
        payload: dict[str, Any],
        private_key_hex: str,
        timestamp: int | None = None,
    ) -> "Transaction":
        unsigned = cls(
            type,
            payload,
            public_key_hex(private_key_hex),
            int(time.time()) if timestamp is None else timestamp,
            signature="",
        )
        signature = sign(private_key_hex, canonical_bytes(unsigned.body()))
        return cls(unsigned.type, payload, unsigned.sender, unsigned.timestamp, signature)
