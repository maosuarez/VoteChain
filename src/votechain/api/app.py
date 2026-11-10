import hmac
import os
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from votechain import blind
from votechain.auth.mailer import Mailer, mailer_from_env
from votechain.auth.service import VoterAuth
from votechain.blockchain import Blockchain
from votechain.crypto import public_key_hex
from votechain.mempool import Mempool
from votechain.merkle import merkle_proof
from votechain.p2p_http import NodeRunner, p2p_router, runner_from_env, runner_lifespan
from votechain.store import IssuerKeyStore
from votechain.transactions import Transaction
from votechain.voting import (
    ADD_CANDIDATE,
    ADD_CATEGORY,
    CAST_BALLOT,
    CLOSE_ELECTION,
    CLOSED,
    CREATE_ELECTION,
    OPEN_ELECTION,
    VotingState,
    build_state,
)

MAX_TXS_PER_BLOCK = 100
WEB_DIR = Path(os.environ.get("VOTECHAIN_WEB_DIR") or Path(__file__).resolve().parents[3] / "web")


class ElectionBody(BaseModel):
    election_id: str
    opens_at: int
    closes_at: int


class CategoryBody(BaseModel):
    category: str


class CandidateBody(BaseModel):
    category: str
    candidate_id: str
    name: str


class RollBody(BaseModel):
    emails: list[str]


class CodeBody(BaseModel):
    email: str


class CredentialBody(BaseModel):
    email: str
    code: str
    blinded: str


class BallotBody(BaseModel):
    tx: dict[str, Any]


def create_app(
    master_token: str,
    master_private_key: str,
    auth: VoterAuth,
    chain: Blockchain | None = None,
    now: Callable[[], int] = lambda: int(time.time()),
    issuer_key_factory: Callable[[], blind.IssuerKey] = blind.generate_issuer_key,
    node: NodeRunner | None = None,
    confirm_timeout: float = 10.0,
) -> FastAPI:
    """Without `node` the API mines locally (PoW, in memory). With `node` it runs on the PoA
    network: actions are handed to the node and confirmed only once included in its chain."""
    if not master_token:
        raise ValueError("master token must not be empty")
    public_key_hex(master_private_key)  # fails fast on an invalid key

    if node is not None:
        chain = node.node.chain
        lock = node.lock  # shared with the node's worker thread
    else:
        chain = chain if chain is not None else Blockchain()
        lock = threading.Lock()  # chain, mempool and SQLite are not thread-safe
    mempool = Mempool()
    app = FastAPI(title="VoteChain", lifespan=runner_lifespan(node) if node else None)
    if node is not None:
        app.include_router(p2p_router(node))

    def require_master(authorization: str | None = Header(default=None)) -> None:
        scheme, _, token = (authorization or "").partition(" ")
        if scheme != "Bearer" or not hmac.compare_digest(token.encode(), master_token.encode()):
            raise HTTPException(401, "unauthorized")

    def wait_included(tx_id: str, from_index: int) -> bool:
        """Poll the node's chain for `tx_id`. Caller holds the lock; it is released while
        waiting because the node's worker needs it to append the block."""
        deadline = time.monotonic() + confirm_timeout
        lock.release()
        try:
            while True:
                with lock:
                    for block in chain.chain[from_index:]:
                        if any(Transaction.from_dict(t).tx_id == tx_id for t in block.data["transactions"]):
                            return True
                if time.monotonic() >= deadline:
                    return False
                time.sleep(0.05)
        finally:
            lock.acquire()

    def submit(tx: Transaction) -> str | None:
        """Validate against the chain-derived state, then mine (or hand to the PoA node).
        Caller holds the lock."""
        timestamp = now()
        reason = build_state(chain).apply(tx, timestamp)
        if reason is not None:
            return reason
        if node is None:
            mempool.add(tx)
            chain.add_block_from_mempool(mempool, MAX_TXS_PER_BLOCK, timestamp)
            return None
        from_index = max(len(chain.chain) - 1, 0)
        node.node.submit_tx(tx)
        if not wait_included(tx.tx_id, from_index):
            raise HTTPException(503, "pending")  # not confirmed: never report it as applied
        return None

    def admin_tx(type: str, payload: dict[str, Any]) -> None:
        tx = Transaction.create(type, payload, master_private_key, timestamp=now())
        reason = submit(tx)
        if reason is not None:
            raise HTTPException(409, reason)

    def require_election(election_id: str) -> None:
        if election_id not in build_state(chain).elections:
            raise HTTPException(409, "unknown election")

    def election_state(election_id: str) -> tuple[VotingState, Any]:
        state = build_state(chain)
        election = state.elections.get(election_id)
        if election is None:
            raise HTTPException(404, "unknown election")
        return state, election

    # --- master ---

    @app.post("/admin/elections", status_code=201, dependencies=[Depends(require_master)])
    def create_election(body: ElectionBody) -> dict[str, Any]:
        issuer = issuer_key_factory()
        with lock:
            try:
                admin_tx(CREATE_ELECTION, {
                    "election_id": body.election_id,
                    "opens_at": body.opens_at,
                    "closes_at": body.closes_at,
                    "issuer_key": issuer.public(),
                })
            except HTTPException as e:
                if e.status_code == 503:  # id was validated as new; keep the key if it lands later
                    auth.set_issuer_key(body.election_id, issuer)
                raise
            auth.set_issuer_key(body.election_id, issuer)
        return {"election_id": body.election_id, "issuer_key": issuer.public()}

    @app.post("/admin/elections/{election_id}/categories", status_code=201,
              dependencies=[Depends(require_master)])
    def add_category(election_id: str, body: CategoryBody) -> dict[str, str]:
        with lock:
            admin_tx(ADD_CATEGORY, {"election_id": election_id, "category": body.category})
        return {"category": body.category}

    @app.post("/admin/elections/{election_id}/candidates", status_code=201,
              dependencies=[Depends(require_master)])
    def add_candidate(election_id: str, body: CandidateBody) -> dict[str, str]:
        with lock:
            admin_tx(ADD_CANDIDATE, {
                "election_id": election_id,
                "category": body.category,
                "candidate_id": body.candidate_id,
                "name": body.name,
            })
        return {"candidate_id": body.candidate_id}

    @app.post("/admin/elections/{election_id}/open", dependencies=[Depends(require_master)])
    def open_election(election_id: str) -> dict[str, str]:
        with lock:
            admin_tx(OPEN_ELECTION, {"election_id": election_id})
        return {"status": "open"}

    @app.post("/admin/elections/{election_id}/close", dependencies=[Depends(require_master)])
    def close_election(election_id: str) -> dict[str, str]:
        with lock:
            admin_tx(CLOSE_ELECTION, {"election_id": election_id})
        return {"status": "closed"}

    @app.post("/admin/elections/{election_id}/voters", dependencies=[Depends(require_master)])
    def load_roll(election_id: str, body: RollBody) -> dict[str, int]:
        with lock:
            require_election(election_id)
            if auth.load_roll(election_id, body.emails) is not None:
                raise HTTPException(400, "invalid email in roll")
        return {"submitted": len(body.emails)}

    @app.post("/admin/elections/{election_id}/codes", dependencies=[Depends(require_master)])
    def send_code(election_id: str, body: CodeBody) -> dict[str, bool]:
        with lock:
            return {"sent": auth.issue_code(election_id, body.email) is None}

    # --- votante ---

    @app.post("/elections/{election_id}/credentials")
    def redeem_credential(election_id: str, body: CredentialBody) -> dict[str, str]:
        with lock:
            blind_signature, reason = auth.redeem_credential(
                election_id, body.email, body.code, body.blinded
            )
        if reason is not None or blind_signature is None:
            raise HTTPException(400, "invalid_request")
        return {"blind_signature": blind_signature}

    @app.post("/ballots", status_code=202)
    def cast_ballot(body: BallotBody) -> dict[str, str]:
        try:
            tx = Transaction.from_dict(body.tx)
            if tx.type != CAST_BALLOT:
                raise ValueError
            with lock:
                reason = submit(tx)
        except (KeyError, TypeError, ValueError, AttributeError):
            reason = "malformed"
        if reason is not None:
            raise HTTPException(400, "ballot_rejected")
        return {"tx_id": tx.tx_id}

    # --- lectura pública ---

    @app.get("/chain")
    def read_chain() -> dict[str, Any]:
        with lock:
            return {
                "length": len(chain.chain),
                "valid": chain.is_valid().valid,
                "blocks": [asdict(b) for b in chain.chain],
            }

    @app.get("/chain/blocks/{index}")
    def read_block(index: int) -> dict[str, Any]:
        with lock:
            if not 0 <= index < len(chain.chain):
                raise HTTPException(404, "unknown block")
            return asdict(chain.chain[index])

    @app.get("/chain/receipts/{tx_id}")
    def read_receipt(tx_id: str) -> dict[str, Any]:
        """Inclusion proof only; no sender, signature or payload (keeps ballots unlinkable)."""
        with lock:
            for block in chain.chain:
                txs = block.data["transactions"]
                for i, tx in enumerate(txs):
                    if Transaction.from_dict(tx).tx_id == tx_id:
                        return {
                            "tx_id": tx_id,
                            "block_index": block.index,
                            "block_hash": block.hash,
                            "merkle_root": block.merkle_root,
                            "proof": merkle_proof(txs, i),
                        }
        raise HTTPException(404, "unknown transaction")

    @app.get("/elections/{election_id}")
    def read_election(election_id: str) -> dict[str, Any]:
        with lock:
            _, election = election_state(election_id)
            return {
                "election_id": election_id,
                "status": election.status,
                "opens_at": election.opens_at,
                "closes_at": election.closes_at,
                "issuer_key": election.issuer_key,
                "categories": election.candidates,
            }

    @app.get("/elections/{election_id}/tally")
    def read_tally(election_id: str) -> dict[str, Any]:
        with lock:
            state, election = election_state(election_id)
            if election.status != CLOSED:
                raise HTTPException(403, "tally available after close")
            return {
                category: [asdict(e) for e in entries]
                for category, entries in state.tally(election_id).items()
            }

    if WEB_DIR.is_dir():  # last, so it never shadows an API route
        app.mount("/explorer", StaticFiles(directory=WEB_DIR, html=True), name="explorer")

    return app


def create_app_from_env(mailer: Mailer, db_path: str = ":memory:") -> FastAPI:
    """Master token y clave de firma desde VOTECHAIN_MASTER_TOKEN / VOTECHAIN_MASTER_KEY."""
    return create_app(
        os.environ.get("VOTECHAIN_MASTER_TOKEN", ""),
        os.environ["VOTECHAIN_MASTER_KEY"],
        VoterAuth(mailer, db_path=db_path),
    )


def create_api_from_env(env: dict[str, str] | None = None) -> FastAPI:
    """API as a (non-validator) node of the PoA network, with persistent state in DATA_DIR."""
    env = os.environ if env is None else env
    data_dir = Path(env.get("VOTECHAIN_DATA_DIR", "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    auth = VoterAuth(
        mailer_from_env(env, data_dir),
        db_path=str(data_dir / "auth.db"),
        issuer_store=IssuerKeyStore(data_dir / "issuer_keys.json"),
    )
    return create_app(
        env.get("VOTECHAIN_MASTER_TOKEN", ""),
        env["VOTECHAIN_MASTER_KEY"],
        auth,
        node=runner_from_env(env, require_key=False),
        confirm_timeout=float(env.get("VOTECHAIN_CONFIRM_TIMEOUT", "10")),
    )
