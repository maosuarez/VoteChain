import json
import logging
import smtplib
from collections.abc import Mapping
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol


class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class FakeMailer:
    """Mailer en memoria para tests y desarrollo; no envía nada."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))


class SmtpMailer:
    """Entrega por SMTP; STARTTLS por defecto. Las credenciales nunca se registran."""

    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        username: str = "",
        password: str = "",
        starttls: bool = True,
        timeout: float = 10.0,
    ) -> None:
        self._host, self._port, self._sender = host, port, sender
        self._username, self._password = username, password
        self._starttls, self._timeout = starttls, timeout

    def send(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self._sender, to, subject
        message.set_content(body)
        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
            if self._starttls:
                smtp.starttls()
            if self._username:
                smtp.login(self._username, self._password)
            smtp.send_message(message)


class FileMailer:
    """Buzón JSONL solo para desarrollo y e2e: guarda los códigos EN CLARO."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def send(self, to: str, subject: str, body: str) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"to": to, "subject": subject, "body": body}) + "\n")


def mailer_from_env(env: Mapping[str, str], data_dir: str | Path) -> Mailer:
    """SMTP si hay `VOTECHAIN_SMTP_HOST`; si no, buzón en archivo (advertido)."""
    host = env.get("VOTECHAIN_SMTP_HOST", "")
    if not host:
        outbox = Path(data_dir) / "outbox.jsonl"
        logging.getLogger("votechain.mail").warning(
            "VOTECHAIN_SMTP_HOST not set: DEV mailbox %s stores codes in plain text", outbox
        )
        return FileMailer(outbox)
    return SmtpMailer(
        host,
        int(env.get("VOTECHAIN_SMTP_PORT", "587")),
        env.get("VOTECHAIN_SMTP_FROM", "votechain@localhost"),
        env.get("VOTECHAIN_SMTP_USER", ""),
        env.get("VOTECHAIN_SMTP_PASSWORD", ""),
        env.get("VOTECHAIN_SMTP_STARTTLS", "1") != "0",
    )
