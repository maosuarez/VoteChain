"""Regenerate tests/vectors/voter_vectors.json from the backend: `python -m tests.make_voter_vectors`."""
import json
from pathlib import Path

from votechain import blind
from votechain.block import canonical_bytes
from votechain.crypto import public_key_hex, sign
from votechain.transactions import Transaction

VECTORS = Path(__file__).parent / "vectors" / "voter_vectors.json"

ISSUER_E = 65537
# Fixed inputs so the file is reproducible; the issuer key itself is generated once and stored.
VOTER_SEED = "11" * 32
FACTOR_SEED = 0x1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF
EID = "e-ñ1"
PICKS = ["B", "A", "D"]
TS = 1000
MESSAGES = ["", "abc", "ñandú ✓", "votechain-credential-v1:e1:" + "ab" * 32]


def build(issuer: blind.IssuerKey) -> dict:
    public = issuer.public()
    voter_pub = public_key_hex(VOTER_SEED)
    message = blind.credential_message(EID, voter_pub)
    n = issuer.n
    blinded_hex = format(blind._fdh(message, n) * pow(FACTOR_SEED, issuer.e, n) % n, "x")
    blind_sig = blind.sign_blinded(issuer, blinded_hex)
    assert blind_sig is not None
    signature = blind.unblind(public, blind_sig, FACTOR_SEED)
    assert blind.verify(public, signature, message)
    tx = Transaction.create(
        "CAST_BALLOT",
        {"election_id": EID, "category": "profesor", "picks": PICKS, "credential_sig": signature},
        VOTER_SEED,
        timestamp=TS,
    )
    return {
        "issuer": {"n": public["n"], "e": public["e"]},
        "issuer_d": format(issuer.d, "x"),
        "election_id": EID,
        "voter": {"seed": VOTER_SEED, "public": voter_pub},
        "ed25519": [
            {"message_hex": m.encode().hex(), "signature": sign(VOTER_SEED, m.encode())} for m in MESSAGES
        ],
        "fdh": [
            {"message_hex": m.encode().hex(), "value": format(blind._fdh(m.encode(), n), "x")} for m in MESSAGES
        ],
        "credential_message": message.decode(),
        "blind": {
            "factor": format(FACTOR_SEED, "x"),
            "blinded": blinded_hex,
            "blind_signature": blind_sig,
            "signature": signature,
        },
        "tx": {
            "dict": tx.to_dict(),
            "tx_id": tx.tx_id,
            "canonical_body": canonical_bytes(tx.body()).decode(),
        },
    }


if __name__ == "__main__":
    # Reuse the stored issuer key when present so regenerating does not churn the file.
    if VECTORS.exists():
        old = json.loads(VECTORS.read_text(encoding="utf-8"))
        key = blind.IssuerKey(int(old["issuer"]["n"], 16), old["issuer"]["e"], int(old["issuer_d"], 16))
    else:
        key = blind.generate_issuer_key()
    VECTORS.write_text(json.dumps(build(key), indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
