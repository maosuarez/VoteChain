import hmac
import logging
import re
import secrets
import sqlite3
import time
from hashlib import sha256
from typing import Callable

from votechain import blind
from votechain.auth.mailer import Mailer
from votechain.store import IssuerKeyStore

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
# Base32 sin caracteres ambiguos (0/O, 1/I/L).
_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
_CODE_LEN = 10

_SCHEMA = """
CREATE TABLE IF NOT EXISTS voters (
    election_id TEXT NOT NULL,
    email TEXT NOT NULL,
    credential_issued INTEGER NOT NULL DEFAULT 0,
    issue_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (election_id, email)
);
CREATE TABLE IF NOT EXISTS codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id TEXT NOT NULL,
    email TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id TEXT NOT NULL,
    email TEXT NOT NULL,
    event TEXT NOT NULL,
    ts INTEGER NOT NULL
);
"""


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_code(election_id: str, email: str, code: str) -> str:
    return sha256(f"{election_id}:{email}:{code}".encode()).hexdigest()


class VoterAuth:
    """Censo y códigos de un solo uso por correo. Todo vive fuera de la cadena."""

    def __init__(
        self,
        mailer: Mailer,
        db_path: str = ":memory:",
        now: Callable[[], int] = lambda: int(time.time()),
        code_ttl: int = 600,
        max_attempts: int = 5,
        max_issues: int = 3,
        issuer_store: IssuerKeyStore | None = None,
    ) -> None:
        self._mailer = mailer
        self._now = now
        self._ttl = code_ttl
        self._max_attempts = max_attempts
        self._max_issues = max_issues
        self._issuer_store = issuer_store
        # Nunca en SQLite: en memoria y, si se pasa `issuer_store`, en un archivo 0600.
        self._issuer_keys: dict[str, blind.IssuerKey] = issuer_store.load() if issuer_store else {}
        self._db = sqlite3.connect(db_path, check_same_thread=False)  # el acceso lo serializa la API
        self._db.executescript(_SCHEMA)

    # --- censo ---

    def load_roll(self, election_id: str, emails: list[str]) -> str | None:
        """Carga el censo completo o nada. Devuelve None o el motivo de rechazo."""
        normalized = [normalize_email(e) for e in emails]
        if any(not _EMAIL_RE.match(e) for e in normalized):
            return "invalid_email"
        with self._db:
            self._db.executemany(
                "INSERT OR IGNORE INTO voters (election_id, email) VALUES (?, ?)",
                [(election_id, e) for e in set(normalized)],
            )
        return None

    def is_eligible(self, election_id: str, email: str) -> bool:
        return self._voter(election_id, normalize_email(email)) is not None

    def has_credential(self, election_id: str, email: str) -> bool:
        row = self._voter(election_id, normalize_email(email))
        return bool(row and row[0])

    # --- códigos ---

    def issue_code(self, election_id: str, email: str) -> str | None:
        """Genera y envía un código. Devuelve None o el motivo de rechazo."""
        email = normalize_email(email)
        voter = self._voter(election_id, email)
        if voter is None:
            return self._reject(election_id, email, "not_eligible")
        credential_issued, issue_count = voter
        if credential_issued:
            return self._reject(election_id, email, "already_received")
        if issue_count >= self._max_issues:
            return self._reject(election_id, email, "resend_limit")

        code = "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LEN))
        with self._db:
            self._db.execute(
                "UPDATE codes SET active = 0 WHERE election_id = ? AND email = ?",
                (election_id, email),
            )
            self._db.execute(
                "INSERT INTO codes (election_id, email, code_hash, expires_at) VALUES (?, ?, ?, ?)",
                (election_id, email, _hash_code(election_id, email, code), self._now() + self._ttl),
            )
            self._db.execute(
                "UPDATE voters SET issue_count = issue_count + 1 WHERE election_id = ? AND email = ?",
                (election_id, email),
            )
            self._log(election_id, email, "issued")
        try:
            self._mailer.send(email, "Código de votación", f"Tu código de un solo uso: {code}")
        except Exception as e:  # SMTP errors can embed credentials/addresses: log the type only
            logging.getLogger("votechain.mail").warning("send failed: %s", type(e).__name__)
            return self._reject(election_id, email, "mail_failed")
        return None

    def redeem_code(self, election_id: str, email: str, code: str) -> str | None:
        """Canjea el código y marca al votante. Devuelve None o el motivo de rechazo."""
        email = normalize_email(email)
        row = self._db.execute(
            "SELECT id, code_hash, expires_at, attempts FROM codes "
            "WHERE election_id = ? AND email = ? AND active = 1 ORDER BY id DESC LIMIT 1",
            (election_id, email),
        ).fetchone()
        if row is None:
            return self._reject(election_id, email, "no_active_code")
        code_id, code_hash, expires_at, attempts = row
        if attempts >= self._max_attempts:
            return self._reject(election_id, email, "attempts_exhausted")
        if self._now() >= expires_at:
            return self._reject(election_id, email, "expired")
        if not hmac.compare_digest(code_hash, _hash_code(election_id, email, code.strip().upper())):
            with self._db:
                self._db.execute("UPDATE codes SET attempts = attempts + 1 WHERE id = ?", (code_id,))
            return self._reject(election_id, email, "wrong_code")
        with self._db:
            self._db.execute("UPDATE codes SET active = 0 WHERE id = ?", (code_id,))
            self._db.execute(
                "UPDATE voters SET credential_issued = 1 WHERE election_id = ? AND email = ?",
                (election_id, email),
            )
            self._log(election_id, email, "redeemed")
        return None

    # --- credenciales anónimas ---

    def set_issuer_key(self, election_id: str, key: blind.IssuerKey) -> None:
        self._issuer_keys[election_id] = key
        if self._issuer_store is not None:
            self._issuer_store.save(self._issuer_keys)

    def redeem_credential(
        self, election_id: str, email: str, code: str, blinded: str
    ) -> tuple[str | None, str | None]:
        """Canjea el código y firma a ciegas. Devuelve (firma_ciega, None) o (None, motivo).

        Ni el valor ciego ni la firma se persisten ni se registran: así el master no
        puede unir el canje de un correo con ninguna credencial de la cadena.
        """
        key = self._issuer_keys.get(election_id)
        if key is None:
            return None, self._reject(election_id, normalize_email(email), "no_issuer_key")
        if not blind.is_valid_blinded(key.public(), blinded):
            return None, self._reject(election_id, normalize_email(email), "invalid_blinded")
        reason = self.redeem_code(election_id, email, code)
        if reason is not None:
            return None, reason
        return blind.sign_blinded(key, blinded), None

    def audit_log(self, election_id: str) -> list[tuple[str, str, int]]:
        """Eventos (correo, evento, ts) en orden de ocurrencia."""
        return self._db.execute(
            "SELECT email, event, ts FROM audit WHERE election_id = ? ORDER BY id", (election_id,)
        ).fetchall()

    # --- internos ---

    def _voter(self, election_id: str, email: str) -> tuple[int, int] | None:
        return self._db.execute(
            "SELECT credential_issued, issue_count FROM voters WHERE election_id = ? AND email = ?",
            (election_id, email),
        ).fetchone()

    def _log(self, election_id: str, email: str, event: str) -> None:
        self._db.execute(
            "INSERT INTO audit (election_id, email, event, ts) VALUES (?, ?, ?, ?)",
            (election_id, email, event, self._now()),
        )

    def _reject(self, election_id: str, email: str, reason: str) -> str:
        with self._db:
            self._log(election_id, email, f"rejected:{reason}")
        return reason
