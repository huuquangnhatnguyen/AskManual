"""Eval harness (AS2.1): recall@k per query type, for any registered retriever.

    python -m eval.run --retriever keyword
    python -m eval.run --retriever baseline --misses       # also list every question that missed
    python -m eval.run --retriever fused --answers         # also citation accuracy (needs AS4.1 + a key)

Swapping retrievers is a flag, not an edit: anything in retrieval/registry.py runs here unchanged.
Every run is written to eval/results/<retriever>.json, so each number in the final
table (AS7.2) traces to a committed file.
"""
import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from eval.metrics import citation_correct, first_rank, hit_at_k
from retrieval import registry
from retrieval.base import Retriever

DATA = Path(__file__).parent / "data"
RESULTS = Path(__file__).parent / "results"
QUERY_TYPES = ["prose", "table", "diagram", "fault_code"]


def load_gold(path: Path = DATA / "gold.jsonl") -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def groups(g: dict) -> list[str]:
    """Rows a question counts toward. Slices overlap on purpose; OVERALL counts each once."""
    out = [g["query_type"]]
    if g.get("cross_manual"):
        out.append("cross_manual")
    if g.get("scan_target"):
        out.append("scanned")
    return out + ["OVERALL"]


def cited_pages(answer) -> set[tuple[str, int]]:
    return {(s.doc_id, s.page) for s in answer.sources.values()}


def evaluate(retriever: str | Retriever, gold: list[dict], k: int = 5, answers: bool = False) -> dict:
    retriever = registry.get(retriever) if isinstance(retriever, str) else retriever
    if answers:
        from api.pipeline import answer_question  # imports generation; only when asked
    rows = []
    t0 = time.time()
    for g in gold:
        hits = retriever.search(g["question"], k=max(k, 20))
        row = {
            "id": g["id"], "groups": groups(g),
            "hit": hit_at_k(hits, g, k), "rank": first_rank(hits, g),
            "top": [f"{h.doc_id}:p{h.page}" for h in hits[:k]],
        }
        if answers:
            resp = answer_question(g["question"], retriever=retriever)
            row["refused"] = resp.kind == "refusal"
            row["cite_ok"] = False if row["refused"] else citation_correct(cited_pages(resp), g)
        rows.append(row)

    table = defaultdict(lambda: {"n": 0, "hits": 0, "cite_ok": 0})
    for r in rows:
        for grp in r["groups"]:
            t = table[grp]
            t["n"] += 1
            t["hits"] += r["hit"]
            t["cite_ok"] += r.get("cite_ok", False)
    return {
        "retriever": retriever.name, "k": k, "answers": answers,
        "seconds": round(time.time() - t0, 1),
        "table": {grp: dict(v) for grp, v in table.items()},
        "questions": rows,
    }


def render(result: dict) -> str:
    k, table = result["k"], result["table"]
    cite = result["answers"]
    head = f"{'type':15} {'n':>3} {f'recall@{k}':>9}" + (f" {'cite_acc':>9}" if cite else "")
    lines = [head]
    for grp in [*QUERY_TYPES, "cross_manual", "scanned", "OVERALL"]:
        t = table.get(grp)
        if not t:
            lines.append(f"{grp:15} {'-':>3} {'n/a':>9}")
            continue
        line = f"{grp:15} {t['n']:>3} {t['hits'] / t['n']:>9.2f}"
        if cite:
            line += f" {t['cite_ok'] / t['n']:>9.2f}"
        lines.append(line)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--retriever", default="keyword", choices=registry.names())
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--gold", type=Path, default=DATA / "gold.jsonl")
    ap.add_argument("--answers", action="store_true", help="also generate answers and score citations")
    ap.add_argument("--misses", action="store_true", help="list questions whose gold page missed the top k")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    result = evaluate(args.retriever, load_gold(args.gold), args.k, args.answers)
    print(render(result))
    if args.misses:
        print("\nmisses:")
        for r in result["questions"]:
            if not r["hit"]:
                print(f"  {r['id']}  gold rank={r['rank']}  top={r['top']}")
    if not args.no_save:
        RESULTS.mkdir(exist_ok=True)
        out = RESULTS / f"{args.retriever}{'_answers' if args.answers else ''}.json"
        out.write_text(json.dumps(result, indent=1), encoding="utf-8")
        print(f"\n-> {out.relative_to(Path.cwd()) if out.is_relative_to(Path.cwd()) else out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
