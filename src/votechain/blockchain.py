import time
from dataclasses import dataclass

from votechain.block import Block

GENESIS_PREV_HASH = "0" * 64
GENESIS_BLOCK = Block.create(
    index=0, timestamp=0, prev_hash=GENESIS_PREV_HASH, data={"genesis": True}
)


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    bad_index: int | None = None
    reason: str = ""


class Blockchain:
    def __init__(self) -> None:
        self.chain: list[Block] = [GENESIS_BLOCK]

    def add_block(self, data: dict, timestamp: int | None = None) -> Block:
        last = self.chain[-1]
        block = Block.create(
            index=len(self.chain),
            timestamp=int(time.time()) if timestamp is None else timestamp,
            prev_hash=last.hash,
            data=data,
        )
        self.chain.append(block)
        return block

    def is_valid(self) -> ValidationResult:
        if not self.chain or self.chain[0] != GENESIS_BLOCK:
            return ValidationResult(False, 0, "genesis block mismatch")
        for i, block in enumerate(self.chain):
            if block.index != i:
                return ValidationResult(False, i, "non-consecutive index")
            if block.hash != block.compute_hash():
                return ValidationResult(False, i, "hash mismatch")
            if i > 0 and block.prev_hash != self.chain[i - 1].hash:
                return ValidationResult(False, i, "prev_hash mismatch")
        return ValidationResult(True)
