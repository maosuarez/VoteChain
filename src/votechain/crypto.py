from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

PUBLIC_KEY_HEX_LEN = 64
SIGNATURE_HEX_LEN = 128


def generate_keypair() -> tuple[str, str]:
    """Return (private_key_hex, public_key_hex); the public key is the identity."""
    private = Ed25519PrivateKey.generate()
    seed = private.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    return seed.hex(), public_key_hex(seed.hex())


def public_key_hex(private_key_hex: str) -> str:
    private = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    return private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()


def sign(private_key_hex: str, message: bytes) -> str:
    private = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    return private.sign(message).hex()


def verify(public_key_hex: str, signature_hex: str, message: bytes) -> bool:
    """Never raises: any malformed input or bad signature yields False."""
    if len(public_key_hex) != PUBLIC_KEY_HEX_LEN or len(signature_hex) != SIGNATURE_HEX_LEN:
        return False
    try:
        public = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public.verify(bytes.fromhex(signature_hex), message)
    except (ValueError, InvalidSignature):
        return False
    return True
