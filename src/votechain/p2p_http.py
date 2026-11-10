"""Real HTTP network for PoA nodes: transport adapter, worker loop and /p2p routes.

`Node` is synchronous and gossips from inside its own calls. With blocking HTTP and one
lock, A -> B -> C -> A would deadlock on A's lock. So inbound gossip only enqueues (the
route returns at once) and a single thread applies messages to the `Node`.
"""
import logging
import os
import queue
import threading
import time
from collections.abc import Mapping
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel

from votechain.consensus import ValidatorSet
from votechain.crypto import public_key_hex
from votechain.network import Node
from votechain.store import ChainStore

log = logging.getLogger("votechain.p2p")


class HttpTransport:
    """`Transport` over HTTP. Network errors are swallowed: a dead peer must not break gossip."""

    def __init__(
        self, peers: Mapping[str, str], timeout: float = 2.0, client: httpx.Client | None = None
    ) -> None:
        self._urls = {k: v.rstrip("/") for k, v in peers.items()}
        self._client = client or httpx.Client(timeout=timeout)

    def peers(self, node_id: str) -> list[str]:
        return [p for p in self._urls if p != node_id]

    def _post(self, dst: str, path: str, body: dict[str, Any]) -> None:
        try:
            self._client.post(f"{self._urls[dst]}{path}", json=body)
        except httpx.HTTPError:
            pass

    def send_tx(self, src: str, dst: str, tx: dict[str, Any]) -> None:
        self._post(dst, "/p2p/tx", {"src": src, "tx": tx})

    def send_block(self, src: str, dst: str, block: dict[str, Any]) -> None:
        self._post(dst, "/p2p/block", {"src": src, "block": block})

    def fetch_chain(self, src: str, dst: str) -> list[dict[str, Any]]:
        try:
            response = self._client.get(f"{self._urls[dst]}/p2p/chain")
            response.raise_for_status()
            blocks = response.json()
        except (httpx.HTTPError, ValueError):
            return []
        return blocks if isinstance(blocks, list) else []


class NodeRunner:
    """Owns a `Node`: one thread applies inbound messages, produces blocks and syncs.

    `lock` guards the node's chain/mempool; share it with anything else that reads or
    mutates them (the HTTP routes and the API).
    """

    def __init__(
        self,
        node: Node,
        store: ChainStore | None = None,
        block_interval: float = 1.0,
        sync_interval: float = 5.0,
    ) -> None:
        self.node = node
        self.store = store
        self.block_interval = block_interval
        self.sync_interval = sync_interval
        self.lock = threading.Lock()
        self._inbox: queue.Queue[tuple[str, str | None, dict[str, Any]]] = queue.Queue(maxsize=10_000)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        if store is not None:
            store.load(node.chain)  # raises ChainStoreError on a tampered file
        # Lock-free view for /p2p/chain and status: peers must never wait on our lock
        # (two nodes syncing from each other under their locks would deadlock).
        self._snapshot: list[dict[str, Any]] = []
        self._refresh_snapshot()

    # --- inbound (called from HTTP threads; never touches the node) ---

    def enqueue(self, kind: str, sender: str | None, message: dict[str, Any]) -> bool:
        try:
            self._inbox.put_nowait((kind, sender, message))
        except queue.Full:
            return False
        return True

    # --- lifecycle ---

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name=f"node-{self.node.node_id}", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        last_produce = last_sync = time.monotonic()
        while not self._stop.is_set():
            try:
                kind, sender, message = self._inbox.get(timeout=0.05)
            except queue.Empty:
                pass
            else:
                self._guard(lambda: self._locked(lambda: self._handle(kind, sender, message)))
            now = time.monotonic()
            if now - last_produce >= self.block_interval:
                last_produce = now
                self._guard(lambda: self._locked(self._produce))
            if now - last_sync >= self.sync_interval:
                last_sync = now
                self._guard(self._sync_cycle)

    def _handle(self, kind: str, sender: str | None, message: dict[str, Any]) -> None:
        if kind == "tx":
            self.node.receive_tx(message, sender)
        else:
            self.node.receive_block(message, sender)

    def _sync_cycle(self) -> None:
        """Fetch peers' chains WITHOUT the lock (slow network), then adopt under it."""
        node = self.node
        fetched = [node.transport.fetch_chain(node.node_id, p) for p in node.transport.peers(node.node_id)]

        def adopt() -> None:
            for raw in fetched:
                node.adopt_chain(raw)
            node.rebroadcast_mempool()

        self._locked(adopt)

    def _produce(self) -> None:
        if len(self.node.mempool):
            self.node.produce_block()

    def _locked(self, action: Any) -> None:
        """Run a node action under the lock; persist and re-snapshot if the chain changed."""
        with self.lock:
            before = (len(self.node.chain.chain), self.node.chain.chain[-1].hash)
            action()
            if (len(self.node.chain.chain), self.node.chain.chain[-1].hash) != before:
                if self.store is not None:
                    self.store.save(self.node.chain)
                self._refresh_snapshot()

    def _guard(self, action: Any) -> None:
        try:
            action()
        except Exception:  # a malformed peer message must not kill the node
            log.exception("node action failed")

    def _refresh_snapshot(self) -> None:
        self._snapshot = [asdict(b) for b in self.node.chain.chain]

    # --- read ---

    def chain_snapshot(self) -> list[dict[str, Any]]:
        return self._snapshot

    def status(self) -> dict[str, Any]:
        snapshot = self._snapshot  # consistent height/tip without taking the lock
        return {
            "node_id": self.node.node_id,
            "height": len(snapshot),
            "tip": snapshot[-1]["hash"],
            "mempool": len(self.node.mempool),
            "peers": self.node.transport.peers(self.node.node_id),
            "validators": len(self.node.chain.validators.keys) if self.node.chain.validators else 0,
            "is_validator": self.node.private_key is not None,
        }


class TxMessage(BaseModel):
    src: str | None = None
    tx: dict[str, Any]


class BlockMessage(BaseModel):
    src: str | None = None
    block: dict[str, Any]


def p2p_router(runner: NodeRunner) -> APIRouter:
    router = APIRouter()

    @router.post("/p2p/tx", status_code=202)
    def receive_tx(msg: TxMessage) -> dict[str, bool]:
        if not runner.enqueue("tx", msg.src, msg.tx):
            raise HTTPException(503, "inbox full")
        return {"queued": True}

    @router.post("/p2p/block", status_code=202)
    def receive_block(msg: BlockMessage) -> dict[str, bool]:
        if not runner.enqueue("block", msg.src, msg.block):
            raise HTTPException(503, "inbox full")
        return {"queued": True}

    @router.get("/p2p/chain")
    def chain() -> list[dict[str, Any]]:
        return runner.chain_snapshot()

    @router.get("/p2p/status")
    def status() -> dict[str, Any]:
        return runner.status()

    return router


def runner_lifespan(runner: NodeRunner) -> Any:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        runner.start()
        try:
            yield
        finally:
            runner.stop()

    return lifespan


def build_node_app(runner: NodeRunner) -> FastAPI:
    """App of a validator process: only the /p2p routes."""
    app = FastAPI(title="VoteChain node", lifespan=runner_lifespan(runner))
    app.include_router(p2p_router(runner))
    return app


# --- configuration from the environment ---


def parse_peers(raw: str) -> dict[str, str]:
    """`id=url,id=url` -> {id: url}."""
    peers: dict[str, str] = {}
    for item in filter(None, (p.strip() for p in raw.split(","))):
        node_id, sep, url = item.partition("=")
        if not sep or not node_id or not url:
            raise ValueError(f"invalid peer entry: {item!r}")
        peers[node_id] = url
    return peers


def parse_validators(raw: str) -> ValidatorSet:
    return ValidatorSet(tuple(k.strip() for k in raw.split(",") if k.strip()))


def runner_from_env(env: Mapping[str, str] | None = None, *, require_key: bool) -> NodeRunner:
    """Build a runner from VOTECHAIN_* variables. `require_key`: validators must hold a key."""
    env = os.environ if env is None else env
    validators = parse_validators(env.get("VOTECHAIN_VALIDATORS", ""))
    node_id = env["VOTECHAIN_NODE_ID"]
    key = env.get("VOTECHAIN_NODE_KEY") or None
    if require_key and key is None:
        raise ValueError("VOTECHAIN_NODE_KEY is required for a validator")
    if key is not None and public_key_hex(key) not in validators:
        raise ValueError("VOTECHAIN_NODE_KEY does not belong to VOTECHAIN_VALIDATORS")
    transport = HttpTransport(parse_peers(env.get("VOTECHAIN_PEERS", "")))
    node = Node(node_id, transport, validators, private_key=key)
    data_dir = Path(env.get("VOTECHAIN_DATA_DIR", "data"))
    return NodeRunner(
        node,
        ChainStore(data_dir / "chain.json"),
        block_interval=float(env.get("VOTECHAIN_BLOCK_INTERVAL", "1")),
        sync_interval=float(env.get("VOTECHAIN_SYNC_INTERVAL", "5")),
    )
