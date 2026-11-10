from votechain.auth.mailer import FakeMailer
from votechain.auth.service import VoterAuth

E, V = "e1", "a@x.edu"


class Clock:
    def __init__(self) -> None:
        self.t = 1000

    def __call__(self) -> int:
        return self.t


def setup(**kw):
    m, c = FakeMailer(), Clock()
    a = VoterAuth(m, now=c, **kw)
    a.load_roll(E, [V])
    return a, m, c


def last_code(m: FakeMailer) -> str:
    return m.sent[-1][2].split(": ")[1]


def test_issue_sends_mail_and_logs():
    a, m, _ = setup()
    assert a.issue_code(E, V) is None
    assert m.sent[-1][0] == V
    assert a.audit_log(E)[0][:2] == (V, "issued")


def test_not_eligible_no_mail():
    a, m, _ = setup()
    assert a.issue_code(E, "z@x.edu") == "not_eligible"
    assert m.sent == []


def test_no_plaintext_persisted():
    a, m, _ = setup()
    a.issue_code(E, V)
    code = last_code(m)
    dump = "\n".join(a._db.iterdump())
    assert code not in dump


def test_expired():
    a, m, c = setup(code_ttl=600)
    a.issue_code(E, V)
    c.t += 600
    assert a.redeem_code(E, V, last_code(m)) == "expired"
    assert not a.has_credential(E, V)


def test_success_and_reuse():
    a, m, _ = setup()
    a.issue_code(E, V)
    code = last_code(m)
    assert a.redeem_code(E, V, code) is None
    assert a.has_credential(E, V)
    assert a.redeem_code(E, V, code) == "no_active_code"


def test_wrong_code_keeps_valid():
    a, m, _ = setup()
    a.issue_code(E, V)
    assert a.redeem_code(E, V, "WRONGCODE1") == "wrong_code"
    assert a.redeem_code(E, V, last_code(m)) is None


def test_attempts_exhausted():
    a, m, _ = setup(max_attempts=5)
    a.issue_code(E, V)
    for _ in range(5):
        assert a.redeem_code(E, V, "WRONGCODE1") == "wrong_code"
    assert a.redeem_code(E, V, last_code(m)) == "attempts_exhausted"
    assert not a.has_credential(E, V)


def test_resend_invalidates_previous():
    a, m, _ = setup()
    a.issue_code(E, V)
    first = last_code(m)
    a.issue_code(E, V)
    assert a.redeem_code(E, V, first) == "wrong_code"
    assert a.redeem_code(E, V, last_code(m)) is None


def test_resend_limit():
    a, m, _ = setup(max_issues=3)
    for _ in range(3):
        assert a.issue_code(E, V) is None
    assert a.issue_code(E, V) == "resend_limit"
    assert len(m.sent) == 3


def test_audit_order_and_no_vote_link():
    a, m, c = setup()
    a.issue_code(E, V)
    c.t += 5
    a.redeem_code(E, V, last_code(m))
    assert [e for _, e, _ in a.audit_log(E)] == ["issued", "redeemed"]
    assert a.audit_log(E)[1][2] == 1005
    cols = [r[1] for r in a._db.execute("PRAGMA table_info(audit)")]
    assert cols == ["id", "election_id", "email", "event", "ts"]
