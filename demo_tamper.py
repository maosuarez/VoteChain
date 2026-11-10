from dataclasses import replace

from votechain.blockchain import Blockchain


def main() -> None:
    bc = Blockchain()
    for n in range(1, 5):
        bc.add_block({"vote": n}, timestamp=n)

    print(f"Before tampering: {bc.is_valid()}")
    bc.chain[2] = replace(bc.chain[2], data={"vote": 999})
    result = bc.is_valid()
    print(f"After tampering block 2: {result}")
    print(f"Chain is {'valid' if result.valid else 'INVALID'}; broken at block {result.bad_index}")


if __name__ == "__main__":
    main()
