from fastapi.testclient import TestClient

from votechain import blind
from votechain.api.app import create_app
from votechain.auth.mailer import FakeMailer
from votechain.auth.service import VoterAuth
from votechain.crypto import generate_keypair, public_key_hex
from votechain.transactions import Transaction

TOKEN = "s3cret"
MASTER_KEY, MASTER_PUB = generate_keypair()
ISSUER = blind.generate_issuer_key()
EID = "e1"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def make_client() -> tuple[TestClient, FakeMailer, VoterAuth]:
    mailer = FakeMailer()
    auth = VoterAuth(mailer)
    app = create_app(TOKEN, MASTER_KEY, auth, now=lambda: 1000, issuer_key_factory=lambda: ISSUER)
    return TestClient(app), mailer, auth


def post(client: TestClient, path: str, body: dict | None = None):
    return client.post(path, json=body or {}, headers=HEADERS)


def open_election(client: TestClient, voters: list[str] | None = None) -> None:
    assert post(client, "/admin/elections", {"election_id": EID, "opens_at": 0, "closes_at": 100000}).status_code == 201
    post(client, f"/admin/elections/{EID}/categories", {"category": "profesor"})
    for c in "ABCD":
        post(client, f"/admin/elections/{EID}/candidates", {"category": "profesor", "candidate_id": c, "name": c})
    if voters:
        assert post(client, f"/admin/elections/{EID}/voters", {"emails": voters}).status_code == 200
    assert post(client, f"/admin/elections/{EID}/open").status_code == 200


def last_code(mailer: FakeMailer) -> str:
    return mailer.sent[-1][2].split(": ")[1]


def get_credential(client: TestClient, mailer: FakeMailer, email: str) -> tuple[str, str]:
    """Full voter side: request code, blind, redeem, unblind. Returns (key, signature)."""
    assert post(client, f"/admin/elections/{EID}/codes", {"email": email}).json() == {"sent": True}
    req = blind.new_credential_request(ISSUER.public(), EID)
    r = client.post(f"/elections/{EID}/credentials", json={"email": email, "code": last_code(mailer), "blinded": req.blinded})
    assert r.status_code == 200
    sig = blind.finish_credential(ISSUER.public(), EID, req, r.json()["blind_signature"])
    return req.private_key, sig


def ballot_tx(key: str, sig: str, picks: list[str]) -> dict:
    payload = {"election_id": EID, "category": "profesor", "picks": picks, "credential_sig": sig}
    return Transaction.create("CAST_BALLOT", payload, key, timestamp=1000).to_dict()
