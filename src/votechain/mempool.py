from collections import OrderedDict

from votechain.transactions import Transaction


class Mempool:
    def __init__(self) -> None:
        self._txs: OrderedDict[str, Transaction] = OrderedDict()

    def __len__(self) -> int:
        return len(self._txs)

    def add(self, tx: Transaction) -> tuple[bool, str]:
        """Return (accepted, reason); reason is empty when accepted."""
        if not tx.verify():
            return False, "invalid signature"
        if tx.tx_id in self._txs:
            return False, "duplicate transaction"
        self._txs[tx.tx_id] = tx
        return True, ""

    def pop_batch(self, max_count: int) -> list[Transaction]:
        """Remove and return up to `max_count` transactions in arrival order."""
        batch: list[Transaction] = []
        while self._txs and len(batch) < max_count:
            _, tx = self._txs.popitem(last=False)
            batch.append(tx)
        return batch

    def remove(self, tx_id: str) -> None:
        self._txs.pop(tx_id, None)

    def pending(self) -> list[Transaction]:
        """Snapshot of waiting transactions in arrival order."""
        return list(self._txs.values())
