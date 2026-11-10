from votechain.crypto import generate_keypair, sign, verify


def test_distinct_identities() -> None:
    assert generate_keypair()[1] != generate_keypair()[1]


def test_public_id_is_64_hex() -> None:
    pub = generate_keypair()[1]
    assert len(pub) == 64 and bytes.fromhex(pub)


def test_valid_signature() -> None:
    priv, pub = generate_keypair()
    assert verify(pub, sign(priv, b"msg"), b"msg")


def test_wrong_message_or_key() -> None:
    priv, pub = generate_keypair()
    sig = sign(priv, b"msg")
    assert not verify(pub, sig, b"other")
    assert not verify(generate_keypair()[1], sig, b"msg")


def test_malformed_inputs_return_false() -> None:
    priv, pub = generate_keypair()
    sig = sign(priv, b"msg")
    assert not verify(pub, "zz" * 64, b"msg")
    assert not verify(pub, sig[:-2], b"msg")
    assert not verify("xyz", sig, b"msg")
    assert not verify("zz" * 32, sig, b"msg")
    assert not verify("", "", b"msg")
