"""RSA blind signatures (Chaum) with full-domain hash, used for anonymous credentials."""
import hashlib
import math
import secrets
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric import rsa

from votechain.crypto import generate_keypair

RSA_BITS = 2048
RSA_EXPONENT = 65537


@dataclass(frozen=True)
class IssuerKey:
    n: int
    e: int
    d: int

    def public(self) -> dict[str, Any]:
        return {"n": format(self.n, "x"), "e": self.e}


@dataclass(frozen=True)
class CredentialRequest:
    """Voter-side secrets of one credential request; only `blinded` goes to the issuer."""

    private_key: str
    public_key: str
    blinded: str
    factor: int


def generate_issuer_key(bits: int = RSA_BITS) -> IssuerKey:
    private = rsa.generate_private_key(RSA_EXPONENT, bits)
    numbers = private.private_numbers()
    return IssuerKey(numbers.public_numbers.n, numbers.public_numbers.e, numbers.d)


def credential_message(election_id: str, credential_public_key: str) -> bytes:
    """What the issuer signs blindly: binds the credential to one election."""
    return f"votechain-credential-v1:{election_id}:{credential_public_key}".encode()


def _parse_public(public: Any) -> tuple[int, int] | None:
    """(n, e) or None when the public key is malformed."""
    try:
        n, e = int(public["n"], 16), public["e"]
    except (KeyError, TypeError, ValueError):
        return None
    if isinstance(e, bool) or not isinstance(e, int) or n < 2**1023 or e < 3 or e % 2 == 0:
        return None
    return n, e


def is_valid_public_key(public: Any) -> bool:
    return _parse_public(public) is not None


def _fdh(message: bytes, n: int) -> int:
    """Full-domain hash: SHA-256 in counter mode, truncated so the value is < n."""
    length = (n.bit_length() - 1) // 8
    out = b""
    counter = 0
    while len(out) < length:
        out += hashlib.sha256(counter.to_bytes(4, "big") + message).digest()
        counter += 1
    return int.from_bytes(out[:length], "big")


def _parse_value(value_hex: str, n: int) -> int | None:
    try:
        value = int(value_hex, 16)
    except (TypeError, ValueError):
        return None
    return value if 0 < value < n else None


def is_valid_blinded(public: Any, blinded_hex: str) -> bool:
    parsed = _parse_public(public)
    return parsed is not None and _parse_value(blinded_hex, parsed[0]) is not None


def blind(public: Any, message: bytes) -> tuple[str, int]:
    """Return (blinded_hex, factor); keep the factor secret to unblind later."""
    parsed = _parse_public(public)
    if parsed is None:
        raise ValueError("malformed issuer public key")
    n, e = parsed
    while True:
        factor = secrets.randbelow(n - 2) + 2
        if math.gcd(factor, n) == 1:
            break
    return format(_fdh(message, n) * pow(factor, e, n) % n, "x"), factor


def sign_blinded(key: IssuerKey, blinded_hex: str) -> str | None:
    """Sign without seeing the message; None if the value is malformed or out of range."""
    value = _parse_value(blinded_hex, key.n)
    if value is None:
        return None
    return format(pow(value, key.d, key.n), "x")


def unblind(public: Any, blind_signature_hex: str, factor: int) -> str:
    n, _ = _parse_public(public) or (0, 0)
    value = _parse_value(blind_signature_hex, n)
    if value is None:
        raise ValueError("malformed blind signature")
    return format(value * pow(factor, -1, n) % n, "x")


def verify(public: Any, signature_hex: str, message: bytes) -> bool:
    """Never raises: malformed input or a bad signature yields False."""
    parsed = _parse_public(public)
    if parsed is None or not isinstance(signature_hex, str):
        return False
    n, e = parsed
    signature = _parse_value(signature_hex, n)
    return signature is not None and pow(signature, e, n) == _fdh(message, n)


def new_credential_request(public: Any, election_id: str) -> CredentialRequest:
    private_key, public_key = generate_keypair()
    blinded, factor = blind(public, credential_message(election_id, public_key))
    return CredentialRequest(private_key, public_key, blinded, factor)


def finish_credential(
    public: Any, election_id: str, request: CredentialRequest, blind_signature_hex: str
) -> str | None:
    """Unblind and check the result; return the credential signature or None if invalid."""
    try:
        signature = unblind(public, blind_signature_hex, request.factor)
    except ValueError:
        return None
    message = credential_message(election_id, request.public_key)
    return signature if verify(public, signature, message) else None
