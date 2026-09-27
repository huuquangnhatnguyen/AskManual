"""Ingest the corpus into chunks.jsonl and pages/*.png.

Run:  python -m ingest.run corpus/
      python -m ingest.run corpus/ --only acs580_firmware_manual --no-render

One process per document. Page renders are skipped if already on disk.
"""
import argparse
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pymupdf

from ingest.corpus import FAMILIES
from ingest.parse import parse_document

DPI = 150


def ingest_one(pdf: Path, pages_dir: Path | None) -> tuple[str, list[str], Counter, float]:
    t0 = time.time()
    doc_id = pdf.stem
    stats: Counter = Counter()
    lines: list[str] = []
    with pymupdf.open(pdf) as doc:
        stats["pages"] = len(doc)
        for page_no, chunks in parse_document(doc, doc_id, FAMILIES[doc_id], stats):
            lines.extend(c.model_dump_json() for c in chunks)
            if pages_dir is not None:
                out = pages_dir / f"{doc_id}_p{page_no:04d}.png"
                if not out.exists():
                    doc[page_no - 1].get_pixmap(dpi=DPI).save(out)
    return doc_id, lines, stats, time.time() - t0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--out", type=Path, default=Path("chunks.jsonl"))
    ap.add_argument("--pages", type=Path, default=Path("pages"))
    ap.add_argument("--only", nargs="*", help="doc_ids to ingest (default: every PDF in corpus)")
    ap.add_argument("--no-render", action="store_true", help="skip page renders")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    pdfs = sorted(args.corpus.glob("*.pdf"))
    if args.only:
        pdfs = [p for p in pdfs if p.stem in set(args.only)]
    unknown = [p.stem for p in pdfs if p.stem not in FAMILIES]
    if unknown:
        print(f"no product_family for {unknown} — add them to ingest/corpus.py", file=sys.stderr)
        return 1
    pages_dir = None if args.no_render else args.pages
    if pages_dir is not None:
        pages_dir.mkdir(parents=True, exist_ok=True)

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(ingest_one, pdfs, [pages_dir] * len(pdfs)))

    total = Counter()
    tmp = args.out.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        print(f"{'doc':34} {'pages':>5} {'no-text':>7} {'prose':>6} {'heading':>7} {'table_row':>9} {'secs':>5}")
        for doc_id, lines, stats, secs in results:
            f.writelines(line + "\n" for line in lines)
            total.update(stats)
            print(f"{doc_id:34} {stats['pages']:>5} {stats['pages_no_text']:>7} {stats['prose']:>6} "
                  f"{stats['heading']:>7} {stats['table_row']:>9} {secs:>5.0f}")
    tmp.replace(args.out)
    n = total["prose"] + total["heading"] + total["table_row"]
    print(f"{'TOTAL':34} {total['pages']:>5} {total['pages_no_text']:>7} {total['prose']:>6} "
          f"{total['heading']:>7} {total['table_row']:>9}")
    print(f"\n{n} chunks -> {args.out}" + ("" if pages_dir is None else f", page renders in {pages_dir}/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
