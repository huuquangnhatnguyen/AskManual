"""Eval harness entry point: `python -m eval.run`.

AS2.1 fills this in with recall@k per query type. For now it loads the gold
set so the module path and data location are fixed.
"""
import json
import sys
from pathlib import Path

DATA = Path(__file__).parent / "data"


def load_gold(path: Path = DATA / "gold.jsonl") -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> int:
    gold = load_gold()
    print(f"{len(gold)} gold questions loaded from {DATA / 'gold.jsonl'}")
    print("No retriever yet (AS2.1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
