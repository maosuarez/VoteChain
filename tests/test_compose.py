import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from votechain import cli

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"
spec = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
services = spec["services"]


def test_services_defined() -> None:
    assert set(services) == {"v1", "v2", "v3", "v4", "v5", "api", "frontend"}
    assert services["v4"]["profiles"] == ["extended"] == services["v5"]["profiles"]
    assert "profiles" not in services["v1"]


def test_validators_publish_no_host_ports() -> None:
    for name in ("v1", "v2", "v3", "v4", "v5"):
        assert "ports" not in services[name], name


def test_public_services_bind_to_configurable_local_interface() -> None:
    for name in ("api", "frontend"):
        (port,) = services[name]["ports"]
        assert port.startswith("${VOTECHAIN_BIND:-127.0.0.1}:"), port


def test_secrets_come_from_env_not_literals() -> None:
    env = services["api"]["environment"]
    assert env["VOTECHAIN_MASTER_TOKEN"].startswith("${") and env["VOTECHAIN_MASTER_KEY"].startswith("${")
    for name in ("v1", "v2", "v3"):  # each validator gets only its own key
        assert services[name]["environment"]["VOTECHAIN_NODE_KEY"].startswith("${VOTECHAIN_NODE_KEY_V")
    assert "VOTECHAIN_NODE_KEY" not in env


def test_every_service_has_persistent_volume() -> None:
    for name in ("v1", "v2", "v3", "v4", "v5", "api"):
        assert services[name]["volumes"] == [f"{name}-data:/data"]
        assert f"{name}-data" in spec["volumes"]


def test_env_file_is_ignored_and_not_tracked() -> None:
    assert ".env" in (ROOT / ".gitignore").read_text().splitlines()
    tracked = subprocess.run(["git", "ls-files", ".env"], cwd=ROOT, capture_output=True, text=True).stdout
    assert tracked == ""
    assert ".env" in (ROOT / ".dockerignore").read_text().splitlines()


docker = shutil.which("docker")


def compose_services(env_file: Path) -> list[str]:
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "--env-file", str(env_file), "config", "--services"],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return sorted(result.stdout.split())


@pytest.mark.skipif(docker is None, reason="docker not installed; `docker compose config` not executed")
def test_docker_compose_config_valid_for_3_and_5_validators(tmp_path, capsys) -> None:
    three, five = tmp_path / "three.env", tmp_path / "five.env"
    assert cli.main(["init", "--validators", "3", "--env-file", str(three)]) == 0
    assert cli.main(["init", "--validators", "5", "--env-file", str(five)]) == 0
    assert compose_services(three) == ["api", "frontend", "v1", "v2", "v3"]
    assert compose_services(five) == ["api", "frontend", "v1", "v2", "v3", "v4", "v5"]


@pytest.mark.skipif(docker is None, reason="docker not installed; `docker compose config` not executed")
def test_compose_refuses_to_start_without_env(tmp_path) -> None:
    empty = tmp_path / "empty.env"
    empty.write_text("")
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE), "--env-file", str(empty), "config"],
        capture_output=True, text=True, timeout=60, env={"PATH": "/usr/bin:/bin"},
    )
    assert result.returncode != 0 and "votechain init" in result.stderr
