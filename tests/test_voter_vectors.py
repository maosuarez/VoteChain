import json

from tests.make_voter_vectors import VECTORS, build
from votechain import blind
from votechain.transactions import Transaction

vec = json.loads(VECTORS.read_text(encoding="utf-8"))


def test_voter_vectors_match_backend() -> None:
    """Stored vectors still equal what the backend computes (detects backend drift)."""
    key = blind.IssuerKey(int(vec["issuer"]["n"], 16), vec["issuer"]["e"], int(vec["issuer_d"], 16))
    assert build(key) == vec


def test_vector_credential_and_tx_verify() -> None:
    message = blind.credential_message(vec["election_id"], vec["voter"]["public"])
    assert blind.verify(vec["issuer"], vec["blind"]["signature"], message)
    assert Transaction.from_dict(vec["tx"]["dict"]).verify()
