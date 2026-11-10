from votechain import blind
from votechain.crypto import generate_keypair, public_key_hex
from votechain.transactions import Transaction
from votechain.voting import VotingState

EID = "e1"
ISSUER = blind.generate_issuer_key()


def tx(key: str, type: str, payload: dict, ts: int = 100) -> Transaction:
    return Transaction.create(type, payload, key, timestamp=ts)


def draft_election(state: VotingState, admin: str, opens_at: int = 0, closes_at: int = 1000) -> None:
    assert state.apply(tx(admin, "CREATE_ELECTION", {"election_id": EID, "opens_at": opens_at, "closes_at": closes_at, "issuer_key": ISSUER.public()}), 1) is None
    for cat in ("profesor",):
        assert state.apply(tx(admin, "ADD_CATEGORY", {"election_id": EID, "category": cat}), 1) is None
        for c in "ABCD":
            assert state.apply(tx(admin, "ADD_CANDIDATE", {"election_id": EID, "category": cat, "candidate_id": c, "name": c}), 1) is None


def open_election(admin: str | None = None, **kw) -> tuple[VotingState, str]:
    admin = admin or generate_keypair()[0]
    state = VotingState()
    draft_election(state, admin, **kw)
    assert state.apply(tx(admin, "OPEN_ELECTION", {"election_id": EID}), 1) is None
    return state, admin


def credential_sig(key: str, election_id: str = EID, issuer: blind.IssuerKey = ISSUER) -> str:
    """Run the real blind-issuance protocol for the credential whose key is `key`."""
    pub = issuer.public()
    blinded, factor = blind.blind(pub, blind.credential_message(election_id, public_key_hex(key)))
    return blind.unblind(pub, blind.sign_blinded(issuer, blinded), factor)


def ballot(key: str, picks: list, category: str = "profesor") -> Transaction:
    payload = {"election_id": EID, "category": category, "picks": picks, "credential_sig": credential_sig(key)}
    return tx(key, "CAST_BALLOT", payload)
