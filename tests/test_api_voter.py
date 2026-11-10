from tests.api_helpers import EID, ISSUER, ballot_tx, get_credential, make_client, open_election, post
from votechain import blind


def redeem(client, email, code, blinded, eid=EID):
    return client.post(f"/elections/{eid}/credentials", json={"email": email, "code": code, "blinded": blinded})


def test_full_flow_redeem_then_ballot_counts():
    client, mailer, _ = make_client()
    open_election(client, ["a@x.edu"])
    key, sig = get_credential(client, mailer, "a@x.edu")
    r = client.post("/ballots", json={"tx": ballot_tx(key, sig, ["A", "B", "C"])})
    assert r.status_code == 202
    post(client, f"/admin/elections/{EID}/close")
    tally = client.get(f"/elections/{EID}/tally").json()["profesor"]
    assert [(e["candidate_id"], e["points"]) for e in tally[:3]] == [("A", 3), ("B", 2), ("C", 1)]


def test_redeem_failures_are_indistinguishable():
    client, mailer, _ = make_client()
    open_election(client, ["a@x.edu"])
    post(client, f"/admin/elections/{EID}/codes", {"email": "a@x.edu"})
    blinded = blind.new_credential_request(ISSUER.public(), EID).blinded
    responses = [
        redeem(client, "nobody@x.edu", "AAAAAAAAAA", blinded),
        redeem(client, "a@x.edu", "WRONGCODE1", blinded),
        redeem(client, "a@x.edu", "AAAAAAAAAA", "zz"),
        redeem(client, "a@x.edu", "AAAAAAAAAA", blinded, eid="nope"),
    ]
    assert {(r.status_code, r.text) for r in responses} == {(400, '{"detail":"invalid_request"}')}


def test_second_redeem_rejected():
    client, mailer, _ = make_client()
    open_election(client, ["a@x.edu"])
    get_credential(client, mailer, "a@x.edu")
    code = mailer.sent[-1][2].split(": ")[1]
    r = redeem(client, "a@x.edu", code, "00")
    assert (r.status_code, r.json()) == (400, {"detail": "invalid_request"})


def test_double_vote_rejected():
    client, mailer, _ = make_client()
    open_election(client, ["a@x.edu"])
    key, sig = get_credential(client, mailer, "a@x.edu")
    assert client.post("/ballots", json={"tx": ballot_tx(key, sig, ["A", "B", "C"])}).status_code == 202
    length = client.get("/chain").json()["length"]
    r = client.post("/ballots", json={"tx": ballot_tx(key, sig, ["B", "A", "C"])})
    assert r.status_code == 400
    assert client.get("/chain").json()["length"] == length


def test_ballot_route_rejects_other_tx_types():
    client, _, _ = make_client()
    from tests.api_helpers import ISSUER
    from votechain.crypto import generate_keypair
    from votechain.transactions import Transaction
    k, _ = generate_keypair()
    tx = Transaction.create("CREATE_ELECTION", {"election_id": "evil", "opens_at": 0, "closes_at": 9, "issuer_key": ISSUER.public()}, k, timestamp=1).to_dict()
    r = client.post("/ballots", json={"tx": tx})
    assert (r.status_code, r.json()) == (400, {"detail": "ballot_rejected"})
    assert client.get("/chain").json()["length"] == 1


def test_ballot_rejections_are_indistinguishable():
    client, mailer, _ = make_client()
    open_election(client, ["a@x.edu"])
    key, sig = get_credential(client, mailer, "a@x.edu")
    fake = ballot_tx(key, "ab" * 10, ["A", "B", "C"])
    bad_picks = ballot_tx(key, sig, ["A", "A", "C"])
    unsigned = {**ballot_tx(key, sig, ["A", "B", "C"]), "signature": "00" * 64}
    responses = [client.post("/ballots", json={"tx": t}) for t in (fake, bad_picks, unsigned, {"x": 1})]
    assert {(r.status_code, r.text) for r in responses} == {(400, '{"detail":"ballot_rejected"}')}


def test_ballot_after_close_rejected():
    client, mailer, _ = make_client()
    open_election(client, ["a@x.edu"])
    key, sig = get_credential(client, mailer, "a@x.edu")
    post(client, f"/admin/elections/{EID}/close")
    assert client.post("/ballots", json={"tx": ballot_tx(key, sig, ["A", "B", "C"])}).status_code == 400


def test_voter_routes_leave_no_link_between_email_and_ballot():
    client, mailer, auth = make_client()
    open_election(client, ["a@x.edu"])
    key, sig = get_credential(client, mailer, "a@x.edu")
    client.post("/ballots", json={"tx": ballot_tx(key, sig, ["A", "B", "C"])})
    chain_text = client.get("/chain").text
    assert "a@x.edu" not in chain_text
    stored = str(auth._db.execute("SELECT * FROM audit").fetchall() + auth._db.execute("SELECT * FROM codes").fetchall())
    assert sig not in stored and key not in stored
