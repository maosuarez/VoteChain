from dataclasses import dataclass, replace
from typing import Any

from votechain.block import Block
from votechain.crypto import PUBLIC_KEY_HEX_LEN, public_key_hex, sign, verify


@dataclass(frozen=True)
class ValidatorSet:
    """Ordered, fixed set of validator public keys (hex)."""

    keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.keys:
            raise ValueError("validator set must not be empty")
        if len(set(self.keys)) != len(self.keys):
            raise ValueError("duplicate validator")
        if any(len(k) != PUBLIC_KEY_HEX_LEN for k in self.keys):
            raise ValueError("invalid validator key")

    def proposer_for(self, index: int) -> str:
        """Round-robin: block `index` belongs to validator `index mod N`."""
        return self.keys[index % len(self.keys)]

    def __contains__(self, key: object) -> bool:
        return key in self.keys


def seal_block(
    index: int,
    timestamp: int,
    prev_hash: str,
    data: dict[str, Any],
    merkle_root: str,
    private_key_hex: str,
) -> Block:
    """Build a block proposed and signed by `private_key_hex` (turn is not checked)."""
    unsigned = Block.create(
        index, timestamp, prev_hash, data, merkle_root,
        proposer=public_key_hex(private_key_hex),
    )
    return replace(unsigned, signature=sign(private_key_hex, unsigned.hash.encode()))


def authority_error(block: Block, validators: ValidatorSet) -> str | None:
    """Reason the block violates PoA rules, or None if it is authorized and signed."""
    if block.proposer not in validators:
        return "unauthorized proposer"
    if block.proposer != validators.proposer_for(block.index):
        return "proposer out of turn"
    if not verify(block.proposer, block.signature, block.hash.encode()):
        return "invalid block signature"
    return None
