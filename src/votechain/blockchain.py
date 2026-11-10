import time
from dataclasses import dataclass

from votechain.block import Block, meets_difficulty
from votechain.consensus import ValidatorSet, authority_error
from votechain.mempool import Mempool
from votechain.merkle import merkle_root
from votechain.transactions import Transaction

GENESIS_PREV_HASH = "0" * 64
GENESIS_BLOCK = Block.create(
    index=0,
    timestamp=0,
    prev_hash=GENESIS_PREV_HASH,
    data={"transactions": []},
    merkle_root=merkle_root([]),
)


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    bad_index: int | None = None
    reason: str = ""


class Blockchain:
    def __init__(
        self, difficulty: int = 0, validators: ValidatorSet | None = None
    ) -> None:
        """With `validators` the chain is PoA (difficulty ignored); otherwise PoW."""
        self.difficulty = difficulty
        self.validators = validators
        self.chain: list[Block] = [GENESIS_BLOCK]

    def mine_block(
        self, data: dict, timestamp: int | None = None
    ) -> tuple[Block, int]:
        """Mine and append a block; return (block, attempts)."""
        block, attempts = Block.mine(
            index=len(self.chain),
            timestamp=int(time.time()) if timestamp is None else timestamp,
            prev_hash=self.chain[-1].hash,
            data=data,
            merkle_root=merkle_root(data["transactions"]),
            difficulty=self.difficulty,
        )
        self.chain.append(block)
        return block, attempts

    def add_block(self, data: dict, timestamp: int | None = None) -> Block:
        return self.mine_block(data, timestamp)[0]

    def add_block_from_mempool(
        self, mempool: Mempool, max_txs: int, timestamp: int | None = None
    ) -> Block:
        """Mine a block with a mempool batch, skipping txs already on chain."""
        included = {
            Transaction.from_dict(t).tx_id
            for b in self.chain
            for t in b.data["transactions"]
        }
        batch = [tx for tx in mempool.pop_batch(max_txs) if tx.tx_id not in included]
        return self.add_block({"transactions": [tx.to_dict() for tx in batch]}, timestamp)

    def is_valid(self) -> ValidationResult:
        if not self.chain or self.chain[0] != GENESIS_BLOCK:
            return ValidationResult(False, 0, "genesis block mismatch")
        seen_tx_ids: set[str] = set()
        for i, block in enumerate(self.chain):
            if block.index != i:
                return ValidationResult(False, i, "non-consecutive index")
            if block.hash != block.compute_hash():
                return ValidationResult(False, i, "hash mismatch")
            if i > 0 and block.prev_hash != self.chain[i - 1].hash:
                return ValidationResult(False, i, "prev_hash mismatch")
            tx_dicts = block.data.get("transactions")
            if not isinstance(tx_dicts, list):
                return ValidationResult(False, i, "missing transactions")
            if block.merkle_root != merkle_root(tx_dicts):
                return ValidationResult(False, i, "merkle root mismatch")
            for tx_dict in tx_dicts:
                try:
                    tx = Transaction.from_dict(tx_dict)
                    signed_ok = tx.verify()
                    tx_id = tx.tx_id
                except (KeyError, TypeError):
                    return ValidationResult(False, i, "malformed transaction")
                if not signed_ok:
                    return ValidationResult(False, i, "invalid transaction signature")
                if tx_id in seen_tx_ids:
                    return ValidationResult(False, i, "replayed transaction")
                seen_tx_ids.add(tx_id)
            if i > 0 and self.validators is not None:
                reason = authority_error(block, self.validators)
                if reason is not None:
                    return ValidationResult(False, i, reason)
            elif i > 0 and not meets_difficulty(block.hash, self.difficulty):
                return ValidationResult(False, i, "insufficient proof of work")
        return ValidationResult(True)

    def try_append(self, block: Block) -> ValidationResult:
        """Append `block` if the resulting chain is valid; otherwise leave it untouched."""
        self.chain.append(block)
        try:
            result = self.is_valid()
        except (AttributeError, KeyError, TypeError, ValueError):  # untrusted, malformed block
            result = ValidationResult(False, len(self.chain) - 1, "malformed block")
        if not result.valid:
            self.chain.pop()
        return result

    def replace_chain(self, candidate: list[Block]) -> bool:
        """Adopt a valid candidate that is longer, or equal length with a lower tip hash."""
        other = Blockchain(self.difficulty, self.validators)
        other.chain = list(candidate)
        if not other.is_valid().valid:
            return False
        if len(candidate) > len(self.chain) or (
            len(candidate) == len(self.chain) and candidate[-1].hash < self.chain[-1].hash
        ):
            self.chain = other.chain
            return True
        return False
