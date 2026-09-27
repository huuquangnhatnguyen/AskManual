"""AS1.1 acceptance: does the PDF text at each chunk's page + bbox match the chunk?

Run:  python -m ingest.spotcheck                 (10 random chunks, seed printed)
      python -m ingest.spotcheck --n 50 --seed 7
      python -m ingest.spotcheck --id acs580_firmware_manual_p553_c001

For each chunk, the bbox is converted back to PyMuPDF space and the page text
inside it is read. Two scores, over word tokens:
  recall    — share of the chunk's words found in the region (is the chunk's
              text really there?)
  precision — share of the region's words found in the chunk (is the region
              tight, not half the page?)
Rows carry header labels ("Cause: ...") that sit above the row, not inside
it, so "Label: " prefixes are stripped before scoring — for prose too, since
a one-cell table row is kept as prose with its label. Exit 1 if any fails.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

import pymupdf

from ingest.text import clean

MIN_RECALL = 0.9
MIN_PRECISION = 0.8
_WORD = re.compile(r"[a-z0-9]+")


def tokens(s: str) -> list[str]:
    return _WORD.findall(clean(s).lower())


def score(chunk: dict, corpus: Path) -> tuple[float, float, str]:
    with pymupdf.open(corpus / f"{chunk['doc_id']}.pdf") as doc:
        page = doc[chunk["page"] - 1]
        H = page.rect.height
        x0, y0, x1, y1 = chunk["bbox"]
        region = page.get_text("text", clip=pymupdf.Rect(x0, H - y1, x1, H - y0) + (-1, -1, 1, 1))
    # "Code (hex): 2330 | Cause: ..." -> "2330 | ...": labels live in the header row, outside the bbox.
    # rsplit, because some headers contain ": " themselves ("Setting of parameter 95.15: Ex motor enabled").
    # Stripping only drops words, so it's for recall; precision compares against the full text.
    text = " | ".join(part.rsplit(": ", 1)[-1] for part in chunk["text"].split(" | "))
    want, got = tokens(text), tokens(region)
    got_set, full_set = set(got), set(tokens(chunk["text"]))
    recall = sum(t in got_set for t in want) / max(1, len(want))
    precision = sum(t in full_set for t in got) / max(1, len(got))
    return recall, precision, clean(region)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chunks", type=Path, default=Path("chunks.jsonl"))
    ap.add_argument("--corpus", type=Path, default=Path("corpus"))
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--id", nargs="*", help="check these chunk ids instead of a random sample")
    ap.add_argument("-v", action="store_true", help="print chunk text and region text")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    with args.chunks.open(encoding="utf-8") as f:
        chunks = [json.loads(line) for line in f if line.strip()]
    if args.id:
        by_id = {c["chunk_id"]: c for c in chunks}
        sample = [by_id[i] for i in args.id]
    else:
        seed = args.seed if args.seed is not None else random.randrange(10_000)
        print(f"seed {seed}, {args.n} of {len(chunks)} chunks\n")
        sample = random.Random(seed).sample([c for c in chunks if c["chunk_type"] != "figure"], args.n)

    fails = 0
    for c in sample:
        recall, precision, region = score(c, args.corpus)
        ok = recall >= MIN_RECALL and precision >= MIN_PRECISION
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'} {c['chunk_id']:44} {c['chunk_type']:9} "
              f"recall {recall:4.0%}  precision {precision:4.0%}  bbox {c['bbox']}")
        if args.v or not ok:
            print(f"     chunk : {c['text'][:200]}\n     region: {region[:200]}")
    print(f"\n{len(sample) - fails}/{len(sample)} match")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
