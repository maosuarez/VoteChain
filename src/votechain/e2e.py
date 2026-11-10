"""Automated end-to-end election against a running PoA deployment (API + nodes over HTTP).

Used by `tests/test_pilot_e2e.py` (in-process servers) and runnable against compose:
    docker compose exec api python -m votechain.e2e --outbox /data/outbox.jsonl
It does NOT replace the independent human audit (see docs/guia-auditoria.md).
"""
import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import httpx

from votechain import blind
from votechain.audit import AuditReport, audit_chains
from votechain.consensus import ValidatorSet
from votechain.p2p_http import parse_peers, parse_validators
from votechain.transactions import Transaction

CATEGORIES = ("administrativo", "profesor")
CANDIDATES = ("A", "B", "C", "D")
POINTS = (3, 2, 1)


@dataclass
class E2EConfig:
    api_url: str
    master_token: str
    node_urls: dict[str, str]  # every node whose chain is audited (validators + api)
    validators: ValidatorSet  # trusted set, supplied independently of the network
    read_code: Callable[[str], str]  # email -> code most recently mailed to it
    election_id: str = "e2e"
    voters: int = 5
    converge_timeout: float = 30.0


@dataclass
class E2EResult:
    report: AuditReport
    expected: dict[str, dict[str, int]]  # category -> candidate -> points, from the casts
    double_vote_status: int = 0
    second_redeem_status: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.report.ok and not self.errors


def picks_for(voter: int, category: int) -> list[str]:
    return [CANDIDATES[(voter + category + k) % len(CANDIDATES)] for k in range(3)]


def expected_points(voters: int) -> dict[str, dict[str, int]]:
    result = {c: {cand: 0 for cand in CANDIDATES} for c in CATEGORIES}
    for v in range(voters):
        for ci, category in enumerate(CATEGORIES):
            for cand, pts in zip(picks_for(v, ci), POINTS):
                result[category][cand] += pts
    return result


def wait_converged(cfg: E2EConfig) -> bool:
    deadline = time.monotonic() + cfg.converge_timeout
    while time.monotonic() < deadline:
        tips = set()
        for url in cfg.node_urls.values():
            try:
                tips.add(httpx.get(f"{url.rstrip('/')}/p2p/status", timeout=5).json()["tip"])
            except (httpx.HTTPError, ValueError, KeyError):
                tips.add(None)
        if len(tips) == 1 and None not in tips:
            return True
        time.sleep(0.2)
    return False


def run_scenario(cfg: E2EConfig) -> E2EResult:
    api = httpx.Client(base_url=cfg.api_url.rstrip("/"), timeout=60)
    admin = {"Authorization": f"Bearer {cfg.master_token}"}
    eid = cfg.election_id

    def post(path: str, body: dict | None = None, headers: dict | None = None) -> httpx.Response:
        return api.post(path, json=body or {}, headers=headers or {})

    def must(response: httpx.Response, *codes: int) -> httpx.Response:
        if response.status_code not in codes:
            raise AssertionError(f"{response.request.url}: {response.status_code} {response.text[:200]}")
        return response

    now = int(time.time())
    must(post("/admin/elections", {"election_id": eid, "opens_at": now - 60, "closes_at": now + 3600}, admin), 201)
    for category in CATEGORIES:
        must(post(f"/admin/elections/{eid}/categories", {"category": category}, admin), 201)
        for cand in CANDIDATES:
            must(post(f"/admin/elections/{eid}/candidates",
                      {"category": category, "candidate_id": cand, "name": f"Candidato {cand}"}, admin), 201)
    emails = [f"votante{i}@fac.edu" for i in range(cfg.voters)]
    must(post(f"/admin/elections/{eid}/voters", {"emails": emails}, admin), 200)
    must(post(f"/admin/elections/{eid}/open", None, admin), 200)
    issuer = must(api.get(f"/elections/{eid}"), 200).json()["issuer_key"]

    result = E2EResult(AuditReport(), expected_points(cfg.voters))
    for v, email in enumerate(emails):
        must(post(f"/admin/elections/{eid}/codes", {"email": email}, admin), 200)
        code = cfg.read_code(email)
        request = blind.new_credential_request(issuer, eid)
        redeemed = must(post(f"/elections/{eid}/credentials",
                             {"email": email, "code": code, "blinded": request.blinded}), 200)
        signature = blind.finish_credential(issuer, eid, request, redeemed.json()["blind_signature"])
        if v == 0:  # the one-time code cannot be redeemed twice
            result.second_redeem_status = post(
                f"/elections/{eid}/credentials", {"email": email, "code": code, "blinded": request.blinded}
            ).status_code
        for ci, category in enumerate(CATEGORIES):
            payload = {"election_id": eid, "category": category, "picks": picks_for(v, ci),
                       "credential_sig": signature}
            tx = Transaction.create("CAST_BALLOT", payload, request.private_key, timestamp=int(time.time()))
            must(post("/ballots", {"tx": tx.to_dict()}), 202)
            if v == 0 and ci == 0:  # same credential, same category, different picks
                again = Transaction.create(
                    "CAST_BALLOT", {**payload, "picks": picks_for(v + 1, ci)},
                    request.private_key, timestamp=int(time.time()) + 1,
                )
                result.double_vote_status = post("/ballots", {"tx": again.to_dict()}).status_code

    must(post(f"/admin/elections/{eid}/close", None, admin), 200)
    published = must(api.get(f"/elections/{eid}/tally"), 200).json()
    if not wait_converged(cfg):
        result.errors.append("nodes did not converge to the same tip in time")

    chains: dict[str, Any] = {}
    for node_id, url in cfg.node_urls.items():
        chains[node_id] = httpx.get(f"{url.rstrip('/')}/p2p/chain", timeout=60).json()
    result.report = audit_chains(chains, cfg.validators, eid, published, use_explorer=True)

    if result.second_redeem_status != 400:
        result.errors.append(f"second code redemption answered {result.second_redeem_status}, expected 400")
    if result.double_vote_status != 400:
        result.errors.append(f"double vote answered {result.double_vote_status}, expected 400")
    if result.report.tally is not None:
        for category, entries in result.report.tally.items():
            got = {e["candidate_id"]: e["points"] for e in entries}
            if got != result.expected[category]:
                result.errors.append(f"{category}: recounted {got} != expected {result.expected[category]}")
    return result


def mailbox_reader(outbox: Path) -> Callable[[str], str]:
    def read(email: str) -> str:
        lines = [json.loads(line) for line in outbox.read_text(encoding="utf-8").splitlines() if line]
        return [m for m in lines if m["to"] == email][-1]["body"].split(": ")[1]

    return read


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m votechain.e2e")
    parser.add_argument("--api", default=os.environ.get("VOTECHAIN_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--token", default=os.environ.get("VOTECHAIN_MASTER_TOKEN", ""))
    parser.add_argument("--nodes", default=os.environ.get("VOTECHAIN_PEERS", ""))
    parser.add_argument("--validators", default=os.environ.get("VOTECHAIN_VALIDATORS", ""))
    parser.add_argument("--outbox", required=True, help="buzón JSONL del FileMailer (solo desarrollo)")
    parser.add_argument("--election", default=f"e2e-{int(time.time())}")
    args = parser.parse_args(argv)
    if not (args.token and args.nodes and args.validators):
        print("faltan --token/--nodes/--validators (o VOTECHAIN_*)", file=sys.stderr)
        return 2
    cfg = E2EConfig(args.api, args.token, parse_peers(args.nodes), parse_validators(args.validators),
                    mailbox_reader(Path(args.outbox)), election_id=args.election)
    result = run_scenario(cfg)
    for problem in [*result.report.findings, *result.errors]:
        print(f"PROBLEMA: {problem}", file=sys.stderr)
    print(f"e2e {'OK' if result.ok else 'FALLÓ'}; altura={result.report.height}; explorador={result.report.explorer}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
