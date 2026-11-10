import json
import socket
import threading

from votechain.auth.mailer import FileMailer, SmtpMailer, mailer_from_env


class FakeSmtpServer:
    """Minimal SMTP server (no TLS/auth) that records the DATA of each message."""

    def __init__(self) -> None:
        self.messages: list[str] = []
        self._sock = socket.socket()
        self._sock.bind(("127.0.0.1", 0))
        self._sock.listen(1)
        self.port = self._sock.getsockname()[1]
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        conn, _ = self._sock.accept()
        with conn, conn.makefile("rwb") as f:
            def reply(line: str) -> None:
                f.write(line.encode() + b"\r\n")
                f.flush()

            reply("220 fake")
            data: list[str] | None = None
            for raw in f:
                line = raw.decode().rstrip("\r\n")
                if data is not None:
                    if line == ".":
                        self.messages.append("\n".join(data))
                        data = None
                        reply("250 queued")
                    else:
                        data.append(line)
                elif line.upper().startswith("DATA"):
                    data = []
                    reply("354 go")
                elif line.upper().startswith("QUIT"):
                    reply("221 bye")
                    return
                else:
                    reply("250 ok")


def test_smtp_mailer_delivers_with_configured_sender() -> None:
    server = FakeSmtpServer()
    SmtpMailer("127.0.0.1", server.port, "vote@fac.edu", starttls=False).send("a@u.edu", "Asunto", "hola")
    assert len(server.messages) == 1
    assert "From: vote@fac.edu" in server.messages[0] and "To: a@u.edu" in server.messages[0]


def test_env_with_host_builds_smtp(tmp_path) -> None:
    m = mailer_from_env({"VOTECHAIN_SMTP_HOST": "smtp.x", "VOTECHAIN_SMTP_PORT": "2525"}, tmp_path)
    assert isinstance(m, SmtpMailer)


def test_env_without_host_uses_file_mailer_and_warns(tmp_path, caplog) -> None:
    with caplog.at_level("WARNING", logger="votechain.mail"):
        m = mailer_from_env({}, tmp_path)
    assert isinstance(m, FileMailer)
    assert "DEV mailbox" in caplog.text
    m.send("a@u.edu", "s", "b")
    assert json.loads((tmp_path / "outbox.jsonl").read_text())["to"] == "a@u.edu"
