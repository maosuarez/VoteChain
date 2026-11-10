"""Real uvicorn servers in threads, bound to ephemeral ports, for network tests."""
import socket
import threading
import time
from pathlib import Path
from typing import Callable

import httpx
import uvicorn
from fastapi import FastAPI

from votechain.api.app import create_app
from votechain.auth.mailer import FakeMailer
from votechain.auth.service import VoterAuth
from votechain.consensus import ValidatorSet
from votechain.crypto import generate_keypair
from votechain.network import Node
from votechain.p2p_http import HttpTransport, NodeRunner, build_node_app
from votechain.store import ChainStore, IssuerKeyStore


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, app: FastAPI, port: int) -> None:
        self.port = port
        self.url = f"http://127.0.0.1:{port}"
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        self._server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
        self._thread = threading.Thread(target=self._server.run, kwargs={"sockets": [sock]}, daemon=True)
        self._thread.start()
        wait_until(lambda: self._server.started, 10)

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=10)


def wait_until(condition: Callable[[], bool], timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.05)
    raise AssertionError("condition not met in time")


class Cluster:
    """N validators over real HTTP. `restart(i)` reuses the node's port and data dir."""

    def __init__(self, tmp_path: Path, n: int = 3, with_api_peer: bool = False) -> None:
        pairs = [generate_keypair() for _ in range(n)]
        self.keys = [p[0] for p in pairs]
        self.validators = ValidatorSet(tuple(p[1] for p in pairs))
        self.ids = [f"v{i + 1}" for i in range(n)]
        self.ports = {i: free_port() for i in self.ids}
        self.api_port = free_port()
        self.tmp_path = tmp_path
        self.servers: dict[str, Server] = {}
        self.runners: dict[str, NodeRunner] = {}
        for i in range(n):
            self.start(i)

    def peers(self) -> dict[str, str]:
        peers = {i: f"http://127.0.0.1:{p}" for i, p in self.ports.items()}
        peers["api"] = f"http://127.0.0.1:{self.api_port}"
        return peers

    def make_runner(self, node_id: str, key: str | None, **kw) -> NodeRunner:
        node = Node(node_id, HttpTransport(self.peers(), timeout=1.0), self.validators, private_key=key)
        return NodeRunner(node, ChainStore(self.tmp_path / node_id / "chain.json"),
                          block_interval=0.1, sync_interval=0.5, **kw)

    def start(self, index: int) -> None:
        node_id = self.ids[index]
        runner = self.make_runner(node_id, self.keys[index])
        self.runners[node_id] = runner
        self.servers[node_id] = Server(build_node_app(runner), self.ports[node_id])

    def stop(self, index: int) -> None:
        self.servers[self.ids[index]].stop()

    def restart(self, index: int) -> None:
        self.stop(index)
        self.start(index)

    def url(self, index: int) -> str:
        return self.servers[self.ids[index]].url

    def heights(self) -> list[int]:
        return [self._status(i).get("height", -1) for i in self.ids]

    def _status(self, node_id: str) -> dict:
        try:
            return httpx.get(self.servers[node_id].url + "/p2p/status", timeout=2).json()
        except httpx.HTTPError:  # stopped node
            return {}

    def tips(self) -> list[str]:
        return [self._status(i).get("tip", "") for i in self.ids]

    def shutdown(self) -> None:
        for s in self.servers.values():
            s.stop()


TOKEN = "s3cret"
MASTER_KEY, _ = generate_keypair()
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


class Api:
    """The API as a non-validator node of a real cluster; `restart` keeps its data dir."""

    def __init__(self, cluster: Cluster, mailer: FakeMailer, timeout: float = 10.0) -> None:
        self.cluster, self.mailer, self.timeout = cluster, mailer, timeout
        self.server: Server | None = None
        self.start()

    def start(self) -> None:
        data = self.cluster.tmp_path / "api"
        data.mkdir(parents=True, exist_ok=True)
        runner = self.cluster.make_runner("api", None)
        auth = VoterAuth(self.mailer, db_path=str(data / "auth.db"),
                         issuer_store=IssuerKeyStore(data / "issuer.json"))
        app = create_app(TOKEN, MASTER_KEY, auth, node=runner, confirm_timeout=self.timeout)
        self.server = Server(app, self.cluster.api_port)
        self.client = httpx.Client(base_url=self.server.url, timeout=30)

    def restart(self) -> None:
        self.stop()
        self.start()

    def stop(self) -> None:
        self.client.close()
        self.server.stop()

    def post(self, path: str, body: dict | None = None) -> httpx.Response:
        return self.client.post(path, json=body or {}, headers=HEADERS)
