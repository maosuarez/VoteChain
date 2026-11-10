"""File persistence for the chain and the per-election issuer keys."""
import json
import os
from dataclasses import asdict
from pathlib import Path

from votechain import blind
from votechain.block import Block
from votechain.blockchain import Blockchain


class ChainStoreError(Exception):
    """The persisted chain exists but is not valid; the process must not start."""


def _atomic_write(path: Path, text: str, mode: int) -> None:
    """Write via a temp file in the same directory, then rename (never a partial file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(tmp, mode)
    os.replace(tmp, path)


class ChainStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self, chain: Blockchain) -> None:
        """Replace `chain` with the persisted one after full validation; no file = no-op."""
        if not self.path.exists():
            return
        try:
            blocks = [Block(**b) for b in json.loads(self.path.read_text(encoding="utf-8"))]
        except (ValueError, TypeError, OSError) as e:
            raise ChainStoreError(f"persisted chain unreadable: {self.path}") from e
        candidate = Blockchain(chain.difficulty, chain.validators)
        candidate.chain = blocks
        result = candidate.is_valid()
        if not result.valid:
            raise ChainStoreError(
                f"persisted chain invalid at block {result.bad_index}: {result.reason}"
            )
        chain.chain = candidate.chain

    def save(self, chain: Blockchain) -> None:
        _atomic_write(self.path, json.dumps([asdict(b) for b in chain.chain]), 0o644)


class IssuerKeyStore:
    """Private RSA issuer keys per election, readable by the owner only (no encryption at rest)."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, blind.IssuerKey]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return {
            eid: blind.IssuerKey(int(k["n"], 16), k["e"], int(k["d"], 16))
            for eid, k in raw.items()
        }

    def save(self, keys: dict[str, blind.IssuerKey]) -> None:
        raw = {
            eid: {"n": format(k.n, "x"), "e": k.e, "d": format(k.d, "x")}
            for eid, k in keys.items()
        }
        _atomic_write(self.path, json.dumps(raw), 0o600)
