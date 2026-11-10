import copy
import shutil

import httpx
import pytest

from tests.net_helpers import Api, Cluster, wait_until
from votechain.audit import audit_chains
from votechain.auth.mailer import FakeMailer
from votechain.e2e import E2EConfig, run_scenario

EID = "e2e"


def mail_code(mailer: FakeMailer):
    return lambda email: [m for m in mailer.sent if m[0] == email][-1][2].split(": ")[1]


@pytest.fixture(scope="module")
def deployment(tmp_path_factory):
    """3 validators + API node on real HTTP; the election runs once for the whole module."""
    cluster = Cluster(tmp_path_factory.mktemp("e2e"))
    api = Api(cluster, FakeMailer())
    nodes = {**{i: cluster.servers[i].url for i in cluster.ids}, "api": api.server.url}
    cfg = E2EConfig(api.server.url, "s3cret", nodes, cluster.validators, mail_code(api.mailer),
                    election_id=EID, voters=5)
    result = run_scenario(cfg)
    yield cluster, api, cfg, result
    api.stop()
    cluster.shutdown()


def test_election_recount_matches_expected_and_published(deployment) -> None:
    _, _, _, result = deployment
    assert result.ok, (result.report.findings, result.errors)
    assert result.report.height and result.report.height > 20  # setup + 10 ballots + close
    assert result.double_vote_status == 400 and result.second_redeem_status == 400
    # 5 voters x 3/2/1 over 4 candidates, per category: totals add up
    assert sum(e["points"] for e in result.report.tally["profesor"]) == 5 * 6


def test_explorer_verifier_result_is_never_hidden(deployment) -> None:
    _, _, _, result = deployment
    if shutil.which("node") is None:
        assert result.report.explorer.startswith("skipped")  # reported as skipped, not passed
        pytest.skip("node not installed; explorer verifier not executed")
    assert result.report.explorer == "ok"


def test_tampered_node_copy_is_detected_with_node_and_block(deployment) -> None:
    cluster, _, cfg, _ = deployment
    chains = {i: httpx.get(f"{u}/p2p/chain").json() for i, u in cfg.node_urls.items()}
    bad = copy.deepcopy(chains["v2"])
    index = next(i for i, b in enumerate(bad) for t in b["data"]["transactions"] if t["type"] == "CAST_BALLOT")
    tx = bad[index]["data"]["transactions"][0]
    tx["payload"]["picks"] = list(reversed(tx["payload"]["picks"]))
    report = audit_chains({**chains, "v2": bad}, cluster.validators, EID)
    assert any(f.startswith(f"v2: invalid at block {index}") for f in report.findings)


def test_restart_of_validator_and_api_keeps_verifiable_state(deployment) -> None:
    cluster, api, cfg, result = deployment
    cluster.restart(0)
    api.restart()
    wait_until(lambda: len(set(cluster.tips())) == 1)
    again = httpx.get(f"{api.server.url}/elections/{EID}/tally").json()
    chains = {i: httpx.get(f"{u}/p2p/chain").json() for i, u in cfg.node_urls.items()}
    report = audit_chains(chains, cluster.validators, EID, again)
    assert report.ok, report.findings
    assert report.tally == result.report.tally
