import json
import os
import stat
from dataclasses import asdict

import pytest

from tests.voting_helpers import ISSUER
from votechain import blind
from votechain.auth.mailer import FakeMailer
from votechain.auth.service import VoterAuth
from votechain.block import Block
from votechain.blockchain import Blockchain
from votechain.store import ChainStore, ChainStoreError, IssuerKeyStore


def chain_with_blocks() -> Blockchain:
    chain = Blockchain()
    chain.add_block({"transactions": []}, 10)
    chain.add_block({"transactions": []}, 20)
    return chain


def test_chain_roundtrip(tmp_path) -> None:
    store = ChainStore(tmp_path / "chain.json")
    chain = chain_with_blocks()
    store.save(chain)
    loaded = Blockchain()
    store.load(loaded)
    assert loaded.chain == chain.chain


def test_missing_file_keeps_genesis(tmp_path) -> None:
    chain = Blockchain()
    ChainStore(tmp_path / "none.json").load(chain)
    assert len(chain.chain) == 1


def test_tampered_chain_refuses_to_load(tmp_path) -> None:
    path = tmp_path / "chain.json"
    ChainStore(path).save(chain_with_blocks())
    raw = json.loads(path.read_text())
    raw[1]["timestamp"] = 999  # hash no longer matches
    path.write_text(json.dumps(raw))
    with pytest.raises(ChainStoreError, match="block 1"):
        ChainStore(path).load(Blockchain())


def test_garbage_file_refuses_to_load(tmp_path) -> None:
    path = tmp_path / "chain.json"
    path.write_text("not json")
    with pytest.raises(ChainStoreError):
        ChainStore(path).load(Blockchain())


def test_save_leaves_no_temp_file(tmp_path) -> None:
    ChainStore(tmp_path / "chain.json").save(chain_with_blocks())
    assert [p.name for p in tmp_path.iterdir()] == ["chain.json"]


def test_issuer_keys_roundtrip_and_private_permissions(tmp_path) -> None:
    store = IssuerKeyStore(tmp_path / "issuer.json")
    store.save({"e1": ISSUER})
    assert store.load() == {"e1": ISSUER}
    assert stat.S_IMODE(os.stat(store.path).st_mode) == 0o600


def test_redeem_after_restart_uses_same_issuer_key(tmp_path) -> None:
    db, keys = str(tmp_path / "auth.db"), IssuerKeyStore(tmp_path / "issuer.json")
    mailer = FakeMailer()
    first = VoterAuth(mailer, db_path=db, issuer_store=keys)
    first.set_issuer_key("e1", ISSUER)
    first.load_roll("e1", ["a@u.edu"])
    assert first.issue_code("e1", "a@u.edu") is None
    code = mailer.sent[-1][2].split(": ")[1]
    del first  # "restart": new objects over the same files

    second = VoterAuth(mailer, db_path=db, issuer_store=IssuerKeyStore(tmp_path / "issuer.json"))
    req = blind.new_credential_request(ISSUER.public(), "e1")
    signature, reason = second.redeem_credential("e1", "a@u.edu", code, req.blinded)
    assert reason is None and signature is not None
    cred = blind.finish_credential(ISSUER.public(), "e1", req, signature)
    assert blind.verify(ISSUER.public(), cred, blind.credential_message("e1", req.public_key))


def test_mail_failure_is_contained(tmp_path) -> None:
    class Broken:
        def send(self, to: str, subject: str, body: str) -> None:
            raise OSError("smtp password=hunter2")

    auth = VoterAuth(Broken())
    auth.load_roll("e1", ["a@u.edu"])
    assert auth.issue_code("e1", "a@u.edu") == "mail_failed"


def test_block_dicts_are_what_the_store_writes(tmp_path) -> None:
    chain = chain_with_blocks()
    ChainStore(tmp_path / "c.json").save(chain)
    assert json.loads((tmp_path / "c.json").read_text()) == [asdict(b) for b in chain.chain]
    assert Block(**json.loads((tmp_path / "c.json").read_text())[0]) == chain.chain[0]
