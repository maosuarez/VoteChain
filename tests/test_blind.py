import pytest

from votechain import blind
from votechain.blind import (
    credential_message,
    finish_credential,
    generate_issuer_key,
    new_credential_request,
    sign_blinded,
    verify,
)

E = "e1"


@pytest.fixture(scope="module")
def issuer():
    return generate_issuer_key()


def test_blind_sign_unblind_verifies(issuer):
    pub = issuer.public()
    blinded, factor = blind.blind(pub, b"msg")
    sig = blind.unblind(pub, sign_blinded(issuer, blinded), factor)
    assert verify(pub, sig, b"msg")


def test_blinded_value_differs_from_message_and_signature(issuer):
    pub = issuer.public()
    blinded, factor = blind.blind(pub, b"msg")
    blind_sig = sign_blinded(issuer, blinded)
    sig = blind.unblind(pub, blind_sig, factor)
    assert blinded != format(blind._fdh(b"msg", issuer.n), "x")
    assert blind_sig != sig


def test_two_blindings_of_same_message_differ(issuer):
    pub = issuer.public()
    assert blind.blind(pub, b"msg")[0] != blind.blind(pub, b"msg")[0]


@pytest.mark.parametrize("bad", ["", "zz", "0", "-5", "f" * 600])
def test_invalid_blinded_rejected(issuer, bad):
    assert sign_blinded(issuer, bad) is None
    assert not blind.is_valid_blinded(issuer.public(), bad)


def test_credential_roundtrip(issuer):
    pub = issuer.public()
    req = new_credential_request(pub, E)
    sig = finish_credential(pub, E, req, sign_blinded(issuer, req.blinded))
    assert sig and verify(pub, sig, credential_message(E, req.public_key))


def test_tampered_signature_fails(issuer):
    pub = issuer.public()
    req = new_credential_request(pub, E)
    sig = finish_credential(pub, E, req, sign_blinded(issuer, req.blinded))
    tampered = format(int(sig, 16) ^ 1, "x")
    assert not verify(pub, tampered, credential_message(E, req.public_key))


def test_other_election_or_key_fails(issuer):
    pub = issuer.public()
    req = new_credential_request(pub, E)
    sig = finish_credential(pub, E, req, sign_blinded(issuer, req.blinded))
    assert not verify(pub, sig, credential_message("e2", req.public_key))
    other = new_credential_request(pub, E)
    assert not verify(pub, sig, credential_message(E, other.public_key))


def test_verify_never_raises(issuer):
    pub = issuer.public()
    for sig in ("", "zz", None, "0", "f" * 700):
        assert verify(pub, sig, b"m") is False
    assert verify({"n": "1", "e": 3}, "1", b"m") is False
    assert verify(None, "1", b"m") is False


def test_finish_rejects_bad_issuer_signature(issuer):
    pub = issuer.public()
    req = new_credential_request(pub, E)
    assert finish_credential(pub, E, req, "zz") is None
    assert finish_credential(pub, E, req, "5") is None
