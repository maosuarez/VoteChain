"""Independent audit: validate each node's chain against TRUSTED validators and recount."""
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from votechain.block import Block
from votechain.blockchain import Blockchain
from votechain.consensus import ValidatorSet
from votechain.voting import build_state

EXPLORER_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "explorer_tally.js"


@dataclass
class AuditReport:
    findings: list[str] = field(default_factory=list)  # every failure, with node and block
    height: int | None = None
    tip: str | None = None
    tally: dict[str, list[dict[str, Any]]] | None = None  # recounted from the chain
    explorer: str = "not run"  # "ok" | "skipped: <why>" | "not run"

    @property
    def ok(self) -> bool:
        return not self.findings


def recount(chain: Blockchain, election_id: str) -> dict[str, list[dict[str, Any]]] | None:
    state = build_state(chain)
    if election_id not in state.elections:
        return None
    return {c: [asdict(e) for e in es] for c, es in state.tally(election_id).items()}


def explorer_tally(blocks: list[dict[str, Any]], election_id: str) -> dict[str, Any] | str:
    """Run the explorer's JS verifier under Node. Returns its output, or a skip reason."""
    node = shutil.which("node")
    if node is None:
        return "skipped: node not installed"
    if not EXPLORER_SCRIPT.is_file():
        return "skipped: scripts/explorer_tally.js not found"
    result = subprocess.run(
        [node, str(EXPLORER_SCRIPT), election_id],
        input=json.dumps(blocks), capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        return f"skipped: explorer verifier failed ({result.stderr.strip()[:200]})"
    return json.loads(result.stdout)


def audit_chains(
    chains: dict[str, list[dict[str, Any]]],
    trusted: ValidatorSet,
    election_id: str | None = None,
    published_tally: dict[str, list[dict[str, Any]]] | None = None,
    use_explorer: bool = False,
) -> AuditReport:
    """`chains`: node id -> blocks as served by the node. `trusted`: validators the auditor
    knows independently (NOT what the network reports)."""
    report = AuditReport()
    valid: dict[str, Blockchain] = {}
    for node_id, raw in chains.items():
        try:
            chain = Blockchain(validators=trusted)
            chain.chain = [Block(**b) for b in raw]
            result = chain.is_valid()
        except (TypeError, KeyError, AttributeError, ValueError):
            report.findings.append(f"{node_id}: malformed chain data")
            continue
        if not result.valid:
            report.findings.append(f"{node_id}: invalid at block {result.bad_index}: {result.reason}")
        else:
            valid[node_id] = chain
    if not valid:
        report.findings.append("no node served a valid chain")
        return report

    reference_id, reference = next(iter(valid.items()))
    report.height, report.tip = len(reference.chain), reference.chain[-1].hash
    for node_id, chain in valid.items():
        if chain.chain != reference.chain:
            kind = "fork" if len(chain.chain) == len(reference.chain) else "height mismatch"
            report.findings.append(
                f"{node_id} differs from {reference_id}: {kind} (heights {len(chain.chain)} vs "
                f"{len(reference.chain)}, tips {chain.chain[-1].hash[:12]} vs {reference.chain[-1].hash[:12]})"
            )
    if election_id is None:
        return report

    report.tally = recount(reference, election_id)
    if report.tally is None:
        report.findings.append(f"election {election_id!r} not found in the chain")
        return report
    if published_tally is not None and published_tally != report.tally:
        report.findings.append("published tally differs from the tally recounted from the chain")
    if use_explorer:
        out = explorer_tally([asdict(b) for b in reference.chain], election_id)
        if isinstance(out, str):
            report.explorer = out
        elif not out["valid"]:
            report.findings.append(f"explorer verifier rejects the chain at block {out['bad_index']}: {out['reason']}")
        elif out["tally"] != report.tally:
            report.findings.append("explorer verifier tally differs from the Python recount")
        else:
            report.explorer = "ok"
    return report
