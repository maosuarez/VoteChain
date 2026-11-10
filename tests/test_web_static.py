from pathlib import Path

from tests.api_helpers import make_client

WEB = Path(__file__).resolve().parents[1] / "web"


def test_explorer_served_without_auth():
    client, _, _ = make_client()
    assert client.get("/explorer/").status_code == 200
    assert "VoteChain" in client.get("/explorer/").text
    assert client.get("/explorer/verify.js").status_code == 200
    assert client.get("/explorer/app.js").status_code == 200


def test_api_routes_not_shadowed():
    client, _, _ = make_client()
    assert client.get("/chain").status_code == 200


def test_static_code_has_no_admin_or_identity_inputs():
    code = "".join(p.read_text(encoding="utf-8").lower() for p in WEB.iterdir())
    for forbidden in ("/admin", "email", "correo", "authorization", "credential", "innerhtml"):
        assert forbidden not in code, forbidden
