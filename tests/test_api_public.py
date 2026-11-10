from tests.api_helpers import EID, ISSUER, ballot_tx, get_credential, make_client, open_election, post


def test_chain_and_block_read_without_auth():
    client, _, _ = make_client()
    open_election(client)
    chain = client.get("/chain").json()
    assert chain["length"] == len(chain["blocks"]) and chain["valid"] is True
    assert client.get("/chain/blocks/1").json() == chain["blocks"][1]


def test_unknown_block_404():
    client, _, _ = make_client()
    assert client.get("/chain/blocks/99").status_code == 404
    assert client.get("/chain/blocks/-1").status_code == 404


def test_election_view():
    client, _, _ = make_client()
    open_election(client)
    e = client.get(f"/elections/{EID}").json()
    assert e["status"] == "open" and e["issuer_key"] == ISSUER.public()
    assert set(e["categories"]["profesor"]) == set("ABCD")
    assert client.get("/elections/none").status_code == 404


def test_tally_only_after_close():
    client, mailer, _ = make_client()
    open_election(client, ["a@x.edu"])
    key, sig = get_credential(client, mailer, "a@x.edu")
    client.post("/ballots", json={"tx": ballot_tx(key, sig, ["A", "B", "C"])})
    assert client.get(f"/elections/{EID}/tally").status_code == 403
    post(client, f"/admin/elections/{EID}/close")
    r = client.get(f"/elections/{EID}/tally")
    assert r.status_code == 200
    top = r.json()["profesor"][0]
    assert (top["candidate_id"], top["points"], top["rank"], top["tied"]) == ("A", 3, 1, False)
    assert client.get("/elections/none/tally").status_code == 404


def test_receipt_proves_inclusion_without_identity():
    client, mailer, _ = make_client()
    open_election(client, ["a@x.edu"])
    key, sig = get_credential(client, mailer, "a@x.edu")
    tx_id = client.post("/ballots", json={"tx": ballot_tx(key, sig, ["A", "B", "C"])}).json()["tx_id"]
    r = client.get(f"/chain/receipts/{tx_id}")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"tx_id", "block_index", "block_hash", "merkle_root", "proof"}
    block = client.get(f"/chain/blocks/{body['block_index']}").json()
    assert (block["hash"], block["merkle_root"]) == (body["block_hash"], body["merkle_root"])
    assert key not in r.text and sig not in r.text


def test_receipt_unknown_tx_404():
    client, _, _ = make_client()
    assert client.get("/chain/receipts/" + "0" * 64).status_code == 404
