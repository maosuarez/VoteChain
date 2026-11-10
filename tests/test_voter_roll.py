from votechain.auth.mailer import FakeMailer
from votechain.auth.service import VoterAuth


def make() -> VoterAuth:
    return VoterAuth(FakeMailer())


def test_load_roll_scoped_per_election():
    a = make()
    assert a.load_roll("e1", ["a@x.edu"]) is None
    assert a.is_eligible("e1", "a@x.edu")
    assert not a.is_eligible("e2", "a@x.edu")


def test_normalization_and_duplicates():
    a = make()
    a.load_roll("e1", ["A@x.edu", " a@x.edu "])
    assert a._db.execute("SELECT COUNT(*) FROM voters").fetchone()[0] == 1
    assert a.is_eligible("e1", "A@X.EDU")


def test_invalid_email_rejects_whole_load():
    a = make()
    assert a.load_roll("e1", ["ok@x.edu", "algo@dominio"]) == "invalid_email"
    assert not a.is_eligible("e1", "ok@x.edu")


def test_not_in_roll_not_eligible():
    assert not make().is_eligible("e1", "z@x.edu")


def test_initial_flag_false_and_blocks_new_code_after_redeem():
    m = FakeMailer()
    a = VoterAuth(m)
    a.load_roll("e1", ["a@x.edu"])
    assert not a.has_credential("e1", "a@x.edu")
    a.issue_code("e1", "a@x.edu")
    code = m.sent[-1][2].split(": ")[1]
    assert a.redeem_code("e1", "a@x.edu", code) is None
    assert a.has_credential("e1", "a@x.edu")
    assert a.issue_code("e1", "a@x.edu") == "already_received"
    assert len(m.sent) == 1
