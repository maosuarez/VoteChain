import time

import httpx
import pytest

from tests.net_helpers import TOKEN, MASTER_KEY, HEADERS, Api, Cluster, wait_until
from votechain import blind
from votechain.auth.mailer import FakeMailer
from votechain.crypto import generate_keypair
from votechain.transactions import Transaction

EID = "e1"


@pytest.fixture
def env(tmp_path):
    cluster = Cluster(tmp_path)
    api = Api(cluster, FakeMailer())
    yield cluster, api
    api.stop()
    cluster.shutdown()


def create_election(api: Api) -> httpx.Response:
    now = int(time.time())
    return api.post("/admin/elections", {"election_id": EID, "opens_at": now - 60, "closes_at": now + 3600})


def chain_txs(cluster: Cluster, index: int) -> list[str]:
    blocks = httpx.get(cluster.url(index) + "/p2p/chain").json()
    return [t["type"] for b in blocks for t in b["data"]["transactions"]]


def test_confirmed_action_is_on_every_node(env) -> None:
    cluster, api = env
    assert create_election(api).status_code == 201
    wait_until(lambda: len(set(cluster.tips())) == 1)
    for i in range(3):
        assert chain_txs(cluster, i) == ["CREATE_ELECTION"]
    assert api.client.get(f"/elections/{EID}").json()["status"] == "draft"


def test_unconfirmed_action_answers_503_and_is_not_applied(tmp_path) -> None:
    cluster = Cluster(tmp_path)
    api = Api(cluster, FakeMailer(), timeout=0.5)
    try:
        for i in range(3):
            cluster.stop(i)
        assert create_election(api).status_code == 503
        assert api.client.get(f"/elections/{EID}").status_code == 404
    finally:
        api.stop()
        cluster.shutdown()


def test_domain_rejection_is_unchanged_and_not_propagated(env) -> None:
    cluster, api = env
    create_election(api)
    wait_until(lambda: len(set(cluster.tips())) == 1)
    height = cluster.heights()
    key, _ = generate_keypair()
    bad = Transaction.create(
        "CAST_BALLOT",
        {"election_id": EID, "category": "profesor", "picks": ["A", "B", "C"], "credential_sig": "00"},
        key, timestamp=1,
    )
    r = api.client.post("/ballots", json={"tx": bad.to_dict()})
    assert (r.status_code, r.json()) == (400, {"detail": "ballot_rejected"})
    time.sleep(1)
    assert cluster.heights() == height


def test_api_restart_keeps_chain_roll_and_issuer_key(env) -> None:
    cluster, api = env
    create_election(api)
    api.post(f"/admin/elections/{EID}/voters", {"emails": ["a@u.edu"]})
    issuer_public = api.client.get(f"/elections/{EID}").json()["issuer_key"]
    api.restart()
    assert api.client.get(f"/elections/{EID}").json()["issuer_key"] == issuer_public
    assert api.post(f"/admin/elections/{EID}/codes", {"email": "a@u.edu"}).json() == {"sent": True}
    code = api.mailer.sent[-1][2].split(": ")[1]
    req = blind.new_credential_request(issuer_public, EID)
    r = api.client.post(f"/elections/{EID}/credentials",
                        json={"email": "a@u.edu", "code": code, "blinded": req.blinded})
    assert r.status_code == 200
    sig = blind.finish_credential(issuer_public, EID, req, r.json()["blind_signature"])
    assert blind.verify(issuer_public, sig, blind.credential_message(EID, req.public_key))


def test_create_api_from_env_builds_persistent_node_api(tmp_path) -> None:
    from fastapi.testclient import TestClient

    from votechain.api.app import create_api_from_env

    _, pub = generate_keypair()
    env = {
        "VOTECHAIN_VALIDATORS": pub, "VOTECHAIN_NODE_ID": "api", "VOTECHAIN_MASTER_TOKEN": TOKEN,
        "VOTECHAIN_MASTER_KEY": MASTER_KEY, "VOTECHAIN_DATA_DIR": str(tmp_path / "d"),
    }
    with TestClient(create_api_from_env(env)) as client:
        assert client.get("/p2p/status").json()["is_validator"] is False
        assert client.get("/chain").json()["length"] == 1
    assert (tmp_path / "d" / "auth.db").exists()
    with pytest.raises(ValueError):
        create_api_from_env({**env, "VOTECHAIN_MASTER_TOKEN": ""})
