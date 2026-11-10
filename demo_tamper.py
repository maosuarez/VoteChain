import time
from dataclasses import replace

from votechain.block import Block
from votechain.blockchain import Blockchain
from votechain.crypto import generate_keypair
from votechain.merkle import merkle_root
from votechain.transactions import Transaction

DIFFICULTY = 16


def main() -> None:
    bc = Blockchain(difficulty=DIFFICULTY)
    private_key, _ = generate_keypair()
    for n in range(1, 5):
        tx = Transaction.create("demo", {"vote": n}, private_key, timestamp=n)
        bc.add_block({"transactions": [tx.to_dict()]}, timestamp=n)

    print(f"Before tampering: {bc.is_valid()}")

    victim = bc.chain[2]
    forged_tx = {**victim.data["transactions"][0], "payload": {"vote": 999}}
    forged_data = {"transactions": [forged_tx]}
    bc.chain[2] = replace(victim, data=forged_data)
    print(f"Tampered tx only: {bc.is_valid()}")

    forged_root = merkle_root(forged_data["transactions"])
    bc.chain[2] = Block.create(
        victim.index, victim.timestamp, victim.prev_hash, forged_data, forged_root
    )
    print(f"Merkle root and hash recomputed (forged tx still has no valid signature): {bc.is_valid()}")

    start = time.perf_counter()
    remined, attempts = Block.mine(
        victim.index, victim.timestamp, victim.prev_hash, forged_data, forged_root, DIFFICULTY
    )
    elapsed = time.perf_counter() - start
    bc.chain[2] = remined
    result = bc.is_valid()
    print(f"Re-mined block 2 ({attempts} attempts, {elapsed:.2f}s): {result}")
    print("The attacker would also need to re-mine every later block.")
    print(f"Chain is {'valid' if result.valid else 'INVALID'}; broken at block {result.bad_index}")


if __name__ == "__main__":
    main()
