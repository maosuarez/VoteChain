from votechain import blind
from votechain.auth.mailer import FakeMailer
from votechain.auth.service import VoterAuth
from tests.test_email_auth import Clock, last_code

E, V = "e1", "a@x.edu"
ISSUER = blind.generate_issuer_key()


def setup():
    m, c = FakeMailer(), Clock()
    a = VoterAuth(m, now=c)
    a.load_roll(E, [V])
    a.set_issuer_key(E, ISSUER)
    return a, m


def test_redeem_delivers_blind_signature_and_marks_voter():
    a, m = setup()
    a.issue_code(E, V)
    req = blind.new_credential_request(ISSUER.public(), E)
    code = last_code(m)
    blind_sig, reason = a.redeem_credential(E, V, code, req.blinded)
    assert reason is None
    sig = blind.finish_credential(ISSUER.public(), E, req, blind_sig)
    assert sig is not None
    assert a.has_credential(E, V)
    assert a.redeem_credential(E, V, code, req.blinded) == (None, "no_active_code")


def test_invalid_blinded_does_not_consume_code():
    a, m = setup()
    a.issue_code(E, V)
    code = last_code(m)
    assert a.redeem_credential(E, V, code, "zz") == (None, "invalid_blinded")
    assert not a.has_credential(E, V)
    req = blind.new_credential_request(ISSUER.public(), E)
    assert a.redeem_credential(E, V, code, req.blinded)[1] is None


def test_no_issuer_key_does_not_consume_code():
    a, m = setup()
    a.issue_code(E, V)
    req = blind.new_credential_request(ISSUER.public(), E)
    assert a.redeem_credential("other", V, last_code(m), req.blinded)[1] == "no_issuer_key"
    assert a.redeem_credential(E, V, last_code(m), req.blinded)[1] is None


def test_second_redeem_gets_no_second_signature():
    a, m = setup()
    a.issue_code(E, V)
    req = blind.new_credential_request(ISSUER.public(), E)
    assert a.redeem_credential(E, V, last_code(m), req.blinded)[1] is None
    assert a.issue_code(E, V) == "already_received"
    assert a.redeem_credential(E, V, "AAAAAAAAAA", req.blinded)[0] is None


def test_wrong_code_gets_nothing():
    a, m = setup()
    a.issue_code(E, V)
    req = blind.new_credential_request(ISSUER.public(), E)
    assert a.redeem_credential(E, V, "AAAAAAAAAA", req.blinded) == (None, "wrong_code")


def test_nothing_credential_related_persisted_or_logged():
    a, m = setup()
    a.issue_code(E, V)
    req = blind.new_credential_request(ISSUER.public(), E)
    blind_sig, _ = a.redeem_credential(E, V, last_code(m), req.blinded)
    sig = blind.finish_credential(ISSUER.public(), E, req, blind_sig)
    dump = "\n".join(a._db.iterdump()) + repr(a.audit_log(E))
    for secret in (req.blinded, blind_sig, sig, req.public_key):
        assert secret not in dump
    assert [e for _, e, _ in a.audit_log(E)] == ["issued", "redeemed"]
