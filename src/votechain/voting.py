from dataclasses import dataclass, field
from typing import Any

from votechain import blind
from votechain.blockchain import Blockchain
from votechain.transactions import Transaction

CREATE_ELECTION = "CREATE_ELECTION"
ADD_CATEGORY = "ADD_CATEGORY"
ADD_CANDIDATE = "ADD_CANDIDATE"
OPEN_ELECTION = "OPEN_ELECTION"
CAST_BALLOT = "CAST_BALLOT"
CLOSE_ELECTION = "CLOSE_ELECTION"

PICKS_PER_BALLOT = 3
POINTS = (3, 2, 1)

DRAFT, OPEN, CLOSED = "draft", "open", "closed"


@dataclass
class Election:
    admin: str
    opens_at: int
    closes_at: int
    issuer_key: dict[str, Any]
    status: str = DRAFT
    candidates: dict[str, dict[str, str]] = field(default_factory=dict)  # category -> id -> name
    ballots: dict[tuple[str, str], list[str]] = field(default_factory=dict)  # (credential, category) -> picks


@dataclass(frozen=True)
class RankEntry:
    candidate_id: str
    name: str
    points: int
    firsts: int
    seconds: int
    rank: int
    tied: bool


class VotingState:
    """Election state derived by replaying transactions in chain order."""

    def __init__(self) -> None:
        self.elections: dict[str, Election] = {}

    def apply(self, tx: Transaction, block_timestamp: int) -> str | None:
        """Apply a transaction; return None if accepted, else the rejection reason."""
        if not tx.verify():
            return "invalid signature"
        handler = _HANDLERS.get(tx.type)
        if handler is None:
            return "unknown transaction type"
        try:
            return handler(self, tx, block_timestamp)
        except (KeyError, TypeError):
            return "malformed payload"

    def _admin_election(self, tx: Transaction, status: str) -> Election | str:
        election = self.elections.get(tx.payload["election_id"])
        if election is None:
            return "unknown election"
        if tx.sender != election.admin:
            return "sender is not election admin"
        if election.status != status:
            return f"election is not {status}"
        return election

    def _create_election(self, tx: Transaction, _ts: int) -> str | None:
        eid, opens_at, closes_at, issuer_key = (
            tx.payload["election_id"], tx.payload["opens_at"], tx.payload["closes_at"],
            tx.payload["issuer_key"],
        )
        if not isinstance(eid, str) or not eid:
            return "malformed payload"
        if not (isinstance(opens_at, int) and isinstance(closes_at, int)) or opens_at >= closes_at:
            return "invalid window"
        if not blind.is_valid_public_key(issuer_key):
            return "invalid issuer key"
        if eid in self.elections:
            return "election already exists"
        self.elections[eid] = Election(tx.sender, opens_at, closes_at, issuer_key)
        return None

    def _add_category(self, tx: Transaction, _ts: int) -> str | None:
        election = self._admin_election(tx, DRAFT)
        if isinstance(election, str):
            return election
        category = tx.payload["category"]
        if not isinstance(category, str) or not category:
            return "malformed payload"
        if category in election.candidates:
            return "category already exists"
        election.candidates[category] = {}
        return None

    def _add_candidate(self, tx: Transaction, _ts: int) -> str | None:
        election = self._admin_election(tx, DRAFT)
        if isinstance(election, str):
            return election
        category, cid, name = tx.payload["category"], tx.payload["candidate_id"], tx.payload["name"]
        if category not in election.candidates:
            return "unknown category"
        if not (isinstance(cid, str) and cid and isinstance(name, str)):
            return "malformed payload"
        if cid in election.candidates[category]:
            return "candidate already exists"
        election.candidates[category][cid] = name
        return None

    def _open_election(self, tx: Transaction, _ts: int) -> str | None:
        election = self._admin_election(tx, DRAFT)
        if isinstance(election, str):
            return election
        if not election.candidates or any(
            len(c) < PICKS_PER_BALLOT for c in election.candidates.values()
        ):
            return "every category needs at least 3 candidates"
        election.status = OPEN
        return None

    def _close_election(self, tx: Transaction, _ts: int) -> str | None:
        election = self._admin_election(tx, OPEN)
        if isinstance(election, str):
            return election
        election.status = CLOSED
        return None

    def _cast_ballot(self, tx: Transaction, block_timestamp: int) -> str | None:
        election = self.elections.get(tx.payload["election_id"])
        if election is None:
            return "unknown election"
        if election.status != OPEN:
            return "election is not open"
        if not election.opens_at <= block_timestamp <= election.closes_at:
            return "outside election window"
        category, picks = tx.payload["category"], tx.payload["picks"]
        if category not in election.candidates:
            return "unknown category"
        if not isinstance(picks, list) or len(picks) != PICKS_PER_BALLOT:
            return "ballot needs exactly 3 picks"
        if len(set(map(str, picks))) != PICKS_PER_BALLOT or not all(
            isinstance(p, str) and p in election.candidates[category] for p in picks
        ):
            return "picks must be 3 distinct candidates of the category"
        credential_sig = tx.payload.get("credential_sig")
        message = blind.credential_message(tx.payload["election_id"], tx.sender)
        if not blind.verify(election.issuer_key, credential_sig, message):
            return "invalid credential"
        key = (tx.sender, category)
        if key in election.ballots:
            return "credential already voted in category"
        election.ballots[key] = list(picks)
        return None

    def tally(self, election_id: str) -> dict[str, list[RankEntry]]:
        """Ranking per category; ties share rank and are flagged."""
        election = self.elections[election_id]
        result: dict[str, list[RankEntry]] = {}
        for category, candidates in election.candidates.items():
            stats = {cid: [0, 0, 0] for cid in candidates}  # points, firsts, seconds
            for (_, cat), picks in election.ballots.items():
                if cat != category:
                    continue
                for position, cid in enumerate(picks):
                    stats[cid][0] += POINTS[position]
                    if position < 2:
                        stats[cid][position + 1] += 1
            ordered = sorted(stats.items(), key=lambda kv: (-kv[1][0], -kv[1][1], -kv[1][2], kv[0]))
            entries: list[RankEntry] = []
            for cid, key in ordered:
                keys = [s for _, s in ordered]
                tied = keys.count(key) > 1
                rank = keys.index(key) + 1
                entries.append(RankEntry(cid, candidates[cid], key[0], key[1], key[2], rank, tied))
            result[category] = entries
        return result


_HANDLERS: dict[str, Any] = {
    CREATE_ELECTION: VotingState._create_election,
    ADD_CATEGORY: VotingState._add_category,
    ADD_CANDIDATE: VotingState._add_candidate,
    OPEN_ELECTION: VotingState._open_election,
    CLOSE_ELECTION: VotingState._close_election,
    CAST_BALLOT: VotingState._cast_ballot,
}


def build_state(chain: Blockchain) -> VotingState:
    """Replay the chain; invalid domain transactions are ignored deterministically."""
    state = VotingState()
    for block in chain.chain:
        for tx_dict in block.data["transactions"]:
            state.apply(Transaction.from_dict(tx_dict), block.timestamp)
    return state
