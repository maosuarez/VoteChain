import pytest

from tests.api_helpers import EID, HEADERS, ISSUER, MASTER_KEY, MASTER_PUB, TOKEN, make_client, open_election, post
from votechain.api.app import create_app
from votechain.auth.mailer import FakeMailer
from votechain.auth.service import VoterAuth

ADMIN_PATHS = [
    ("/admin/elections", {"election_id": "x", "opens_at": 0, "closes_at": 9}),
    (f"/admin/elections/{EID}/categories", {"category": "c"}),
    (f"/admin/elections/{EID}/open", {}),
    (f"/admin/elections/{EID}/voters", {"emails": []}),
    (f"/admin/elections/{EID}/codes", {"email": "a@x.edu"}),
]


@pytest.mark.parametrize("path,body", ADMIN_PATHS)
def test_admin_requires_token(path, body):
    client, _, _ = make_client()
    for headers in ({}, {"Authorization": "Bearer wrong"}, {"Authorization": f"Basic {TOKEN}"}):
        assert client.post(path, json=body, headers=headers).status_code == 401
    assert client.get("/chain").json()["length"] == 1


def test_empty_token_refuses_to_start():
    with pytest.raises(ValueError):
        create_app("", MASTER_KEY, VoterAuth(FakeMailer()))


def test_actions_are_signed_by_master_on_chain():
    client, _, _ = make_client()
    open_election(client)
    blocks = client.get("/chain").json()["blocks"]
    txs = [t for b in blocks for t in b["data"]["transactions"]]
    assert [t["type"] for t in txs] == ["CREATE_ELECTION", "ADD_CATEGORY"] + ["ADD_CANDIDATE"] * 4 + ["OPEN_ELECTION"]
    assert {t["sender"] for t in txs} == {MASTER_PUB}
    assert client.get(f"/elections/{EID}").json()["status"] == "open"
    assert client.get("/chain").json()["valid"] is True


def test_domain_rejection_is_409_and_chain_does_not_grow():
    client, _, _ = make_client()
    post(client, "/admin/elections", {"election_id": EID, "opens_at": 0, "closes_at": 100})
    post(client, f"/admin/elections/{EID}/categories", {"category": "profesor"})
    length = client.get("/chain").json()["length"]
    r = post(client, f"/admin/elections/{EID}/open")
    assert r.status_code == 409
    assert client.get("/chain").json()["length"] == length


def test_duplicate_election_does_not_replace_issuer_key():
    client, _, auth = make_client()
    open_election(client)
    assert post(client, "/admin/elections", {"election_id": EID, "opens_at": 0, "closes_at": 9}).status_code == 409


def test_issuer_key_public_only():
    client, _, _ = make_client()
    r = post(client, "/admin/elections", {"election_id": EID, "opens_at": 0, "closes_at": 9})
    assert r.json()["issuer_key"] == ISSUER.public()
    assert format(ISSUER.d, "x") not in client.get("/chain").text + r.text


def test_roll_and_resend_stay_off_chain():
    client, mailer, auth = make_client()
    open_election(client)
    length = client.get("/chain").json()["length"]
    assert post(client, f"/admin/elections/{EID}/voters", {"emails": ["a@x.edu"]}).status_code == 200
    assert auth.is_eligible(EID, "a@x.edu")
    assert post(client, f"/admin/elections/{EID}/codes", {"email": "a@x.edu"}).json() == {"sent": True}
    assert mailer.sent[-1][0] == "a@x.edu"
    assert client.get("/chain").json()["length"] == length
    assert "a@x.edu" not in client.get("/chain").text


def test_invalid_email_rejects_whole_roll():
    client, _, auth = make_client()
    open_election(client)
    r = post(client, f"/admin/elections/{EID}/voters", {"emails": ["a@x.edu", "bad"]})
    assert r.status_code == 400
    assert not auth.is_eligible(EID, "a@x.edu")


def test_resend_rejection_gives_no_reason():
    client, mailer, _ = make_client()
    open_election(client, ["a@x.edu"])
    r = post(client, f"/admin/elections/{EID}/codes", {"email": "nobody@x.edu"})
    assert r.json() == {"sent": False}
    assert mailer.sent == []


def test_no_admin_route_exposes_credentials_or_ballots():
    client, _, _ = make_client()
    admin = [r.path for r in client.app.routes if r.path.startswith("/admin")]
    assert not any(w in p for p in admin for w in ("ballot", "credential", "blind", "tally"))


def test_from_env(monkeypatch):
    from fastapi.testclient import TestClient
    from votechain.api.app import create_app_from_env
    monkeypatch.setenv("VOTECHAIN_MASTER_TOKEN", TOKEN)
    monkeypatch.setenv("VOTECHAIN_MASTER_KEY", MASTER_KEY)
    client = TestClient(create_app_from_env(FakeMailer()))
    assert client.post("/admin/elections/x/open").status_code == 401
    monkeypatch.setenv("VOTECHAIN_MASTER_TOKEN", "")
    with pytest.raises(ValueError):
        create_app_from_env(FakeMailer())
