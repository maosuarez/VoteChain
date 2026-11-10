"""Demo "rompe-lo": el master intenta vincular credenciales de la cadena con votantes."""
from votechain import blind
from votechain.auth.mailer import FakeMailer
from votechain.auth.service import VoterAuth
from votechain.blockchain import Blockchain
from votechain.crypto import generate_keypair
from votechain.transactions import Transaction
from votechain.voting import build_state

EID = "demo"
VOTERS = ["ana@uni.edu", "beto@uni.edu", "carla@uni.edu"]


def _tx(key: str, type: str, payload: dict) -> Transaction:
    return Transaction.create(type, payload, key, timestamp=100)


def run() -> tuple[list[str], list[str], list[list[bool]], Blockchain]:
    """Return (blinded values seen by the master, credentials on chain, link matrix, chain)."""
    issuer = blind.generate_issuer_key()
    pub = issuer.public()
    mailer = FakeMailer()
    auth = VoterAuth(mailer)
    auth.load_roll(EID, VOTERS)
    auth.set_issuer_key(EID, issuer)

    admin = generate_keypair()[0]
    txs = [_tx(admin, "CREATE_ELECTION", {"election_id": EID, "opens_at": 0, "closes_at": 1000, "issuer_key": pub}),
           _tx(admin, "ADD_CATEGORY", {"election_id": EID, "category": "profesor"})]
    txs += [_tx(admin, "ADD_CANDIDATE", {"election_id": EID, "category": "profesor", "candidate_id": c, "name": c}) for c in "ABC"]
    txs.append(_tx(admin, "OPEN_ELECTION", {"election_id": EID}))

    seen_by_master: list[str] = []
    for email in VOTERS:
        auth.issue_code(EID, email)
        code = mailer.sent[-1][2].split(": ")[1]
        req = blind.new_credential_request(pub, EID)
        blind_sig, reason = auth.redeem_credential(EID, email, code, req.blinded)
        assert reason is None
        seen_by_master.append(req.blinded)  # lo único que el master recibe del votante
        sig = blind.finish_credential(pub, EID, req, blind_sig)
        payload = {"election_id": EID, "category": "profesor", "picks": ["A", "B", "C"], "credential_sig": sig}
        txs.append(_tx(req.private_key, "CAST_BALLOT", payload))

    chain = Blockchain()
    chain.add_block({"transactions": [t.to_dict() for t in txs]}, timestamp=500)
    credentials = [t.sender for t in txs if t.type == "CAST_BALLOT"]
    assert len(build_state(chain).elections[EID].ballots) == len(VOTERS)

    # El master prueba cada emparejamiento (valor ciego i, credencial j): existe un factor
    # de cegado r que lo explica? Con la clave privada puede calcularlo siempre.
    matrix = []
    for blinded in seen_by_master:
        row = []
        for cred in credentials:
            h = blind._fdh(blind.credential_message(EID, cred), issuer.n)
            r = pow(int(blinded, 16) * pow(h, -1, issuer.n), issuer.d, issuer.n)
            row.append(h * pow(r, issuer.e, issuer.n) % issuer.n == int(blinded, 16))
        matrix.append(row)
    return seen_by_master, credentials, matrix, chain


if __name__ == "__main__":
    _, credentials, matrix, _ = run()
    print("Master: ¿puedo descartar algún emparejamiento valor-ciego -> credencial?")
    for email, row in zip(VOTERS, matrix):
        print(f"  {email}: consistente con {sum(row)}/{len(credentials)} credenciales")
    print("Todos los emparejamientos son posibles: el master no puede vincular." if all(map(all, matrix)) else "VÍNCULO ENCONTRADO")
