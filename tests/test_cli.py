import copy
import os
import stat
import time

import pytest

from tests.net_helpers import MASTER_KEY, TOKEN, Api, Cluster, Server, free_port
from tests.test_audit import TRUSTED, VALIDATOR_KEYS, build_poa_chain
from dataclasses import asdict

from votechain import cli
from votechain.api.app import create_app
from votechain.block import Block
from votechain.blockchain import Blockchain
from votechain.consensus import seal_block
from votechain.merkle import merkle_root
from votechain.auth.mailer import FakeMailer
from votechain.auth.service import VoterAuth
from votechain.crypto import generate_keypair, public_key_hex


def run(capsys, *argv: str) -> tuple[int, str]:
    code = cli.main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def test_help_lists_subcommands(capsys) -> None:
    with pytest.raises(SystemExit) as e:
        cli.main(["--help"])
    assert e.value.code == 0
    out = capsys.readouterr().out
    for name in ("init", "status", "check", "election", "audit"):
        assert name in out


# --- init ---


def test_init_writes_private_env_without_printing_secrets(tmp_path, capsys) -> None:
    path = tmp_path / ".env"
    code, out = run(capsys, "init", "--validators", "3", "--env-file", str(path))
    assert code == 0
    env = cli.load_env_file(path)
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    pubs = env["VOTECHAIN_VALIDATORS"].split(",")
    assert len(pubs) == 3
    for i, pub in enumerate(pubs, start=1):  # order of the set == order of the keys
        assert public_key_hex(env[f"VOTECHAIN_NODE_KEY_V{i}"]) == pub
    assert env["COMPOSE_PROFILES"] == ""
    assert "v3=http://v3:9000" in env["VOTECHAIN_PEERS"] and "api=http://api:8000" in env["VOTECHAIN_PEERS"]
    assert env["VOTECHAIN_MASTER_TOKEN"] not in out and env["VOTECHAIN_MASTER_KEY"] not in out


def test_init_five_validators_enables_extended_profile(tmp_path, capsys) -> None:
    path = tmp_path / ".env"
    assert run(capsys, "init", "--validators", "5", "--env-file", str(path))[0] == 0
    env = cli.load_env_file(path)
    assert env["COMPOSE_PROFILES"] == "extended" and len(env["VOTECHAIN_VALIDATORS"].split(",")) == 5
    assert "VOTECHAIN_NODE_KEY_V5" in env


def test_init_does_not_overwrite(tmp_path, capsys) -> None:
    path = tmp_path / ".env"
    path.write_text("keep")
    code, out = run(capsys, "init", "--env-file", str(path))
    assert code == 1 and path.read_text() == "keep" and "--force" in out
    assert run(capsys, "init", "--env-file", str(path), "--force")[0] == 0


@pytest.mark.parametrize("n", ["2", "6"])
def test_init_rejects_invalid_validator_count(tmp_path, capsys, n) -> None:
    path = tmp_path / ".env"
    assert run(capsys, "init", "--validators", n, "--env-file", str(path))[0] == 1
    assert not path.exists()


# --- election commands (single local API; PoA path is covered by the e2e) ---


@pytest.fixture
def api_url():
    server = Server(create_app(TOKEN, MASTER_KEY, VoterAuth(FakeMailer())), free_port())
    yield server.url
    server.stop()


def test_full_election_cycle_from_cli(api_url, tmp_path, capsys) -> None:
    base = ["election", "--api", api_url, "--token", TOKEN]
    roll = tmp_path / "roll.csv"
    roll.write_text("email\nA@U.edu\nb@u.edu\n")
    now = int(time.time())
    steps = [
        [*base, "create", "e1", "--opens-at", str(now - 60), "--closes-at", str(now + 3600)],
        [*base, "category", "e1", "profesor"],
        *[[*base, "candidate", "e1", "profesor", c, f"Cand {c}"] for c in "ABCD"],
        [*base, "voters", "e1", str(roll)],
        [*base, "code", "e1", "a@u.edu"],
        [*base, "open", "e1"],
        [*base, "close", "e1"],
    ]
    outputs = []
    for step in steps:
        code, out = run(capsys, *step)
        assert code == 0, (step, out)
        outputs.append(out)
    code, out = run(capsys, *base, "tally", "e1")
    assert code == 0 and "Cand A" in out
    assert TOKEN not in "".join(outputs) + out  # the CLI never echoes the token


def test_wrong_token_is_a_readable_error(api_url, capsys) -> None:
    code, out = run(capsys, "election", "--api", api_url, "--token", "nope", "open", "e1")
    assert code == 1 and "401" in out


def test_domain_rejection_is_readable(api_url, capsys) -> None:
    code, out = run(capsys, "election", "--api", api_url, "--token", TOKEN, "open", "ghost")
    assert code == 1 and "409" in out


def test_invalid_csv_row_sends_nothing(tmp_path, capsys) -> None:
    roll = tmp_path / "roll.csv"
    roll.write_text("ok@u.edu\nnot-an-email\n")
    # dead API address: reaching it would produce "no alcanzable", not the row error
    code, out = run(capsys, "election", "--api", "http://127.0.0.1:1", "--token", TOKEN, "voters", "e1", str(roll))
    flat = " ".join(out.split())  # Rich wraps long lines
    assert code == 1 and "fila 2" in flat and "no alcanzable" not in flat


def test_missing_token_is_reported(capsys, monkeypatch) -> None:
    monkeypatch.delenv("VOTECHAIN_MASTER_TOKEN", raising=False)
    code, out = run(capsys, "election", "--api", "http://127.0.0.1:1", "open", "e1")
    assert code == 1 and "VOTECHAIN_MASTER_TOKEN" in out


# --- status / check over a real cluster ---


@pytest.fixture(scope="module")
def net(tmp_path_factory):
    cluster = Cluster(tmp_path_factory.mktemp("net"))
    api = Api(cluster, FakeMailer())
    yield cluster
    api.stop()
    cluster.shutdown()


def nodes_arg(cluster: Cluster) -> str:
    return ",".join(f"{k}={v}" for k, v in cluster.peers().items())


def test_status_and_check_healthy(net, capsys) -> None:
    nodes, vals = nodes_arg(net), ",".join(net.validators.keys)
    code, out = run(capsys, "status", "--nodes", nodes)
    assert code == 0 and "v1" in out and "api" in out
    code, out = run(capsys, "check", "--nodes", nodes, "--validators", vals)
    assert code == 0 and "OK" in out


def test_down_node_is_reported(net, capsys) -> None:
    net.stop(1)
    try:
        nodes, vals = nodes_arg(net), ",".join(net.validators.keys)
        code, out = run(capsys, "status", "--nodes", nodes)
        assert code == 1 and "caído" in out
        code, out = run(capsys, "check", "--nodes", nodes, "--validators", vals)
        assert code == 1 and "v2: no responde" in out
    finally:
        net.start(1)


def test_fork_is_reported(capsys, monkeypatch) -> None:
    a = build_poa_chain()
    b = copy.deepcopy(a)
    b[-1]["timestamp"] += 1  # same height, different tip (and a broken hash)
    status = {"is_validator": True, "height": len(a), "tip": "0" * 64, "mempool": 0}
    chains = {"http://a": a, "http://b": b}

    def fake_get(url: str):
        base = url.rsplit("/p2p/", 1)[0]
        return status if url.endswith("/status") else chains[base]

    monkeypatch.setattr(cli, "get_json", fake_get)
    code, out = run(capsys, "check", "--nodes", "a=http://a,b=http://b", "--validators", ",".join(TRUSTED.keys))
    assert code == 1 and "b: invalid at block" in out


def test_fork_with_valid_chains_is_reported_as_fork(capsys, monkeypatch) -> None:
    base = build_poa_chain()
    chain = Blockchain(validators=TRUSTED)
    chain.chain = [Block(**b) for b in base[:-1]]
    idx = len(chain.chain)
    data = {"transactions": []}
    alt = seal_block(idx, 999, chain.chain[-1].hash, data, merkle_root([]), VALIDATOR_KEYS[idx % 3])
    assert chain.try_append(alt).valid
    forked = [asdict(b) for b in chain.chain]
    status = {"is_validator": True, "height": len(base), "tip": "0" * 64, "mempool": 0}
    chains = {"http://a": base, "http://b": forked}
    monkeypatch.setattr(cli, "get_json", lambda u: status if u.endswith("/status") else chains[u.rsplit("/p2p/", 1)[0]])
    code, out = run(capsys, "check", "--nodes", "a=http://a,b=http://b", "--validators", ",".join(TRUSTED.keys))
    assert code == 1 and "fork" in out


# --- audit ---


@pytest.fixture
def served_chain(monkeypatch):
    chain = build_poa_chain()
    holder = {"chain": chain}
    monkeypatch.setattr(cli, "get_json", lambda url: holder["chain"] if url.endswith("/p2p/chain") else None)
    return holder


def test_audit_ok(served_chain, capsys) -> None:
    code, out = run(capsys, "audit", "e1", "--nodes", "a=http://a,b=http://b",
                    "--validators", ",".join(TRUSTED.keys), "--no-explorer")
    assert code == 0 and "AUDITORÍA OK" in out and "8" in out


def test_audit_tampered_chain(served_chain, capsys) -> None:
    bad = copy.deepcopy(served_chain["chain"])
    bad[5]["data"]["transactions"][0]["payload"]["picks"] = ["D", "C", "B"]
    served_chain["chain"] = bad
    code, out = run(capsys, "audit", "e1", "--nodes", "a=http://a", "--validators", ",".join(TRUSTED.keys),
                    "--no-explorer")
    assert code == 1 and "invalid at block 5" in out


def test_audit_with_other_trusted_validators(served_chain, capsys) -> None:
    other = ",".join(generate_keypair()[1] for _ in range(3))
    code, out = run(capsys, "audit", "e1", "--nodes", "a=http://a", "--validators", other, "--no-explorer")
    assert code == 1 and "unauthorized proposer" in out
