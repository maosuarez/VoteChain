import time
from dataclasses import asdict
from typing import Any, Callable, Protocol

from votechain.block import Block
from votechain.blockchain import Blockchain
from votechain.consensus import ValidatorSet, seal_block
from votechain.crypto import public_key_hex
from votechain.mempool import Mempool
from votechain.merkle import merkle_root
from votechain.transactions import Transaction

MAX_TXS_PER_BLOCK = 100


class Transport(Protocol):
    """Node-to-node channel. Messages are plain dicts so an HTTP adapter can replace it."""

    def peers(self, node_id: str) -> list[str]: ...
    def send_tx(self, src: str, dst: str, tx: dict[str, Any]) -> None: ...
    def send_block(self, src: str, dst: str, block: dict[str, Any]) -> None: ...
    def fetch_chain(self, src: str, dst: str) -> list[dict[str, Any]]: ...


class InMemoryTransport:
    """Synchronous in-process transport with simulated partitions."""

    def __init__(self) -> None:
        self.nodes: dict[str, "Node"] = {}
        self._groups: list[set[str]] | None = None  # None = fully connected

    def register(self, node: "Node") -> None:
        self.nodes[node.node_id] = node

    def partition(self, *groups: set[str]) -> None:
        self._groups = [set(g) for g in groups]

    def heal(self) -> None:
        self._groups = None

    def _reachable(self, a: str, b: str) -> bool:
        if self._groups is None:
            return True
        return any(a in g and b in g for g in self._groups)

    def peers(self, node_id: str) -> list[str]:
        return [n for n in self.nodes if n != node_id and self._reachable(node_id, n)]

    def send_tx(self, src: str, dst: str, tx: dict[str, Any]) -> None:
        if self._reachable(src, dst):
            self.nodes[dst].receive_tx(tx, src)

    def send_block(self, src: str, dst: str, block: dict[str, Any]) -> None:
        if self._reachable(src, dst):
            self.nodes[dst].receive_block(block, src)

    def fetch_chain(self, src: str, dst: str) -> list[dict[str, Any]]:
        if not self._reachable(src, dst):
            return []
        return [asdict(b) for b in self.nodes[dst].chain.chain]


class Node:
    def __init__(
        self,
        node_id: str,
        transport: Transport,
        validators: ValidatorSet,
        private_key: str | None = None,
        now: Callable[[], int] = lambda: int(time.time()),
    ) -> None:
        self.node_id = node_id
        self.transport = transport
        self.private_key = private_key
        self.now = now
        self.chain = Blockchain(validators=validators)
        self.mempool = Mempool()
        if isinstance(transport, InMemoryTransport):
            transport.register(self)

    def _on_chain(self, tx: Transaction) -> bool:
        return any(
            tx.tx_id == Transaction.from_dict(t).tx_id
            for b in self.chain.chain
            for t in b.data["transactions"]
        )

    def _broadcast_tx(self, tx: dict[str, Any], skip: str | None) -> None:
        for peer in self.transport.peers(self.node_id):
            if peer != skip:
                self.transport.send_tx(self.node_id, peer, tx)

    def _broadcast_block(self, block: Block, skip: str | None) -> None:
        for peer in self.transport.peers(self.node_id):
            if peer != skip:
                self.transport.send_block(self.node_id, peer, asdict(block))

    # --- transactions ---

    def submit_tx(self, tx: Transaction) -> bool:
        return self.receive_tx(tx.to_dict(), None)

    def receive_tx(self, tx_dict: dict[str, Any], sender: str | None) -> bool:
        """Accept a new valid tx and gossip it; drop invalid, duplicate or on-chain ones."""
        try:
            tx = Transaction.from_dict(tx_dict)
            if self._on_chain(tx):
                return False
        except (KeyError, TypeError):
            return False
        accepted, _ = self.mempool.add(tx)
        if accepted:
            self._broadcast_tx(tx_dict, sender)
        return accepted

    def rebroadcast_mempool(self) -> None:
        """Re-send waiting txs: a peer that was down (maybe the one on turn) never got them.
        Peers already holding a tx drop it as a duplicate, so this does not storm."""
        for tx in self.mempool.pending():
            self._broadcast_tx(tx.to_dict(), None)

    # --- blocks ---

    def produce_block(self) -> Block | None:
        """Produce and broadcast a block only if this node is the validator on turn."""
        validators = self.chain.validators
        index = len(self.chain.chain)
        if (
            self.private_key is None
            or validators is None
            or validators.proposer_for(index) != public_key_hex(self.private_key)
        ):
            return None
        batch = [
            tx for tx in self.mempool.pop_batch(MAX_TXS_PER_BLOCK)
            if not self._on_chain(tx)
        ]
        data = {"transactions": [tx.to_dict() for tx in batch]}
        block = seal_block(
            index, self.now(), self.chain.chain[-1].hash, data,
            merkle_root(data["transactions"]), self.private_key,
        )
        if not self.chain.try_append(block).valid:
            return None
        self._broadcast_block(block, None)
        return block

    def receive_block(self, block_dict: dict[str, Any], sender: str | None) -> bool:
        """Append a valid block and gossip it; sync with the sender if it does not fit."""
        try:
            block = Block(**block_dict)
        except TypeError:
            return False
        validators = self.chain.validators
        if validators is None or block.proposer not in validators:
            return False  # unauthorized: no append, no gossip, no sync
        if block.index < len(self.chain.chain) and self.chain.chain[block.index] == block:
            return False  # already known
        if self.chain.try_append(block).valid:
            self._drop_included(block)
            self._broadcast_block(block, sender)
            return True
        if sender is not None:
            self._sync_with(sender)
        return False

    def _drop_included(self, block: Block) -> None:
        for t in block.data["transactions"]:
            self.mempool.remove(Transaction.from_dict(t).tx_id)

    # --- sync ---

    def _sync_with(self, peer: str) -> bool:
        return self.adopt_chain(self.transport.fetch_chain(self.node_id, peer))

    def adopt_chain(self, raw_blocks: list[dict[str, Any]]) -> bool:
        """Adopt a peer's chain (as served by `fetch_chain`) if it is better than ours.
        Split from the fetch so a caller can do the network I/O without holding a lock."""
        try:
            candidate = [Block(**b) for b in raw_blocks]
        except TypeError:
            return False
        if not candidate or not self.chain.replace_chain(candidate):
            return False
        for block in self.chain.chain:
            self._drop_included(block)
        return True

    def sync(self) -> bool:
        """Adopt the best chain among reachable peers; True if the chain changed."""
        changed = False
        for peer in self.transport.peers(self.node_id):
            changed = self._sync_with(peer) or changed
        return changed
