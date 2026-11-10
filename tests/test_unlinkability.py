from demo_unlinkability import VOTERS, run


def test_every_pairing_is_consistent() -> None:
    blinded, credentials, matrix, _ = run()
    assert len(blinded) == len(credentials) == len(VOTERS)
    assert all(all(row) for row in matrix)


def test_credentials_unrelated_to_blinded_values() -> None:
    blinded, credentials, _, chain = run()
    on_chain = repr([b.data for b in chain.chain])
    assert not any(b in on_chain for b in blinded)
