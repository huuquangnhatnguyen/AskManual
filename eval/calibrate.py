"""AS3.2 calibration: where does every question's top score land relative to the threshold?

    python -m eval.calibrate --retriever fused
    python -m eval.calibrate --retriever fused --threshold 0.031

Done when all 5 out-of-corpus questions refuse and no gold question does. The
printout suggests the midpoint of the gap when one exists; the chosen value goes
in REFUSAL_THRESHOLD. Commit the output next to the eval results.
"""
import argparse
import json
import sys

from core import config
from eval.run import DATA, load_gold
from retrieval import registry
from retrieval.confidence import top_score


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--retriever", default=config.RETRIEVER, choices=registry.names())
    ap.add_argument("--threshold", type=float, default=config.REFUSAL_THRESHOLD)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    retriever = registry.get(args.retriever)
    ooc = [json.loads(line) for line in (DATA / "out_of_corpus.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    rows = [(g["id"], "gold", top_score(retriever.search(g["question"], k=5))) for g in load_gold()]
    rows += [(q["id"], "ooc", top_score(retriever.search(q["question"], k=5))) for q in ooc]
    rows.sort(key=lambda r: r[2])

    print(f"{'id':6} {'set':5} {'top_score':>10}  refuses@{args.threshold:g}")
    for qid, kind, s in rows:
        refuses = s < args.threshold
        wrong = refuses != (kind == "ooc")
        print(f"{qid:6} {kind:5} {s:>10.4f}  {'yes' if refuses else 'no ':3} {'<-- WRONG' if wrong else ''}")

    worst_ooc = max(s for _, k, s in rows if k == "ooc")
    worst_gold = min(s for _, k, s in rows if k == "gold")
    if worst_ooc < worst_gold:
        print(f"\nseparable: gap ({worst_ooc:.4f}, {worst_gold:.4f}) -> suggest REFUSAL_THRESHOLD={(worst_ooc + worst_gold) / 2:.4f}")
    else:
        print(f"\nNOT separable: highest out-of-corpus {worst_ooc:.4f} >= lowest gold {worst_gold:.4f}")
    ok = all((s < args.threshold) == (k == "ooc") for _, k, s in rows)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
