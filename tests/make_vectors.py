"""Regenerate tests/vectors/audit_vectors.json from the backend: `python -m tests.make_vectors`."""
import json
from pathlib import Path

from tests.api_helpers import EID, ballot_tx, get_credential, make_client, open_election, post
from votechain.block import Block, canonical_bytes
from votechain.merkle import merkle_proof, merkle_root

VECTORS = Path(__file__).parent / "vectors" / "audit_vectors.json"

CANONICAL_INPUTS = [
    {"b": 1, "a": [True, None, "x"], "c": {"z": 0, "y": "ñandú ✓ \u0001"}},
    {"nested": {"k2": [], "k1": {}}, "quote": 'a"b\\c\n'},
]


def _txs(n: int) -> list[dict]:
    return [{"type": "T", "payload": {"i": i, "s": "ñ"}, "sender": "s", "timestamp": i, "signature": ""} for i in range(n)]


def build() -> dict:
    client, mailer, _ = make_client()
    open_election(client, ["a@x.edu", "b@x.edu"])
    tx_ids = []
    for email, picks in (("a@x.edu", ["A", "B", "C"]), ("b@x.edu", ["B", "A", "D"])):
        key, sig = get_credential(client, mailer, email)
        r = client.post("/ballots", json={"tx": ballot_tx(key, sig, picks)})
        tx_ids.append(r.json()["tx_id"])
    post(client, f"/admin/elections/{EID}/close")
    chain = client.get("/chain").json()["blocks"]
    return {
        "sha256": [{"hex": b.hex(), "digest": __import__("hashlib").sha256(b).hexdigest()} for b in (b"", b"abc", b"a" * 1000)],
        "canonical": [{"input": v, "output": canonical_bytes(v).decode()} for v in CANONICAL_INPUTS],
        "merkle": [
            {"txs": txs, "root": merkle_root(txs), "proofs": [merkle_proof(txs, i) for i in range(len(txs))]}
            for txs in map(_txs, (0, 1, 2, 3, 5))
        ],
        "block_hash": [{"block": b, "hash": Block(**b).compute_hash()} for b in chain[:2]],
        "chain": chain,
        "election_id": EID,
        "tally": client.get(f"/elections/{EID}/tally").json(),
        "receipts": [client.get(f"/chain/receipts/{t}").json() for t in tx_ids],
    }


if __name__ == "__main__":
    VECTORS.write_text(json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
