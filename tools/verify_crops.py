"""AS6.3 done-check: does every evidence crop show the region its chunk came from, for all gold questions?

    python tools/verify_crops.py            # check, write index/crop_check/index.html
    python tools/verify_crops.py --min 0.8  # stricter text-recall bar

Two checks per chunk on each gold page, independent of each other:
  geometry  the PDF's own text inside the chunk's bbox (schema bottom-left -> PyMuPDF top-left)
            must contain the chunk's text. A flipped or offset y reads a different strip.
  render    pages/*.png must be the PDF page at 150 dpi, or api/evidence.crop_png scales wrong
            even when the bbox is right.
Then, per gold question, the chunk best matching the answer gist is cropped with the same
crop_png /evidence serves, into a contact sheet for eyeballing.

Gold pages in documents with no chunks (the flattened scan, until AS1.4) are reported, not failed.
Non-zero exit if any chunk fails, so it can gate a commit.
"""
import argparse
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pymupdf  # noqa: E402

from api.evidence import SCALE, crop_png  # noqa: E402
from core import config  # noqa: E402
from core.chunks import chunk_store  # noqa: E402

TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def own_text(chunk) -> str:
    """Chunk text minus what ingest added from elsewhere on the page: cells carry their column
    header as "Header: value", and the header sits outside this chunk's bbox. Ingest does this
    for table rows and for some prose lines lifted out of tables ("Term: COM"), so it's stripped
    for every chunk type; check_chunk scores both forms and keeps the better one."""
    return " ".join(cell.split(": ", 1)[-1] for cell in chunk.text.split(" | "))


def check_chunk(page, chunk) -> float:
    inside = tokens(clip_text(page, chunk.bbox))
    return max(recall(tokens(chunk.text), inside), recall(tokens(own_text(chunk)), inside))


def clip_text(page, bbox) -> str:
    H = page.rect.height
    x0, y0, x1, y1 = bbox
    rect = pymupdf.Rect(x0, H - y1, x1, H - y0)
    words = page.get_text("words")
    # word centre inside the rect: tolerant of glyph boxes that overhang the chunk's bbox
    return " ".join(w[4] for w in words if rect.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)))


def recall(want: list[str], got: list[str]) -> float:
    if not want:
        return 1.0
    pool = set(got)
    return sum(t in pool for t in want) / len(want)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--min", type=float, default=0.7, help="min share of a chunk's tokens found inside its bbox")
    ap.add_argument("--out", type=Path, default=ROOT / "index" / "crop_check")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    gold = [json.loads(l) for l in (ROOT / "eval/data/gold.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    by_page = defaultdict(list)
    for c in chunk_store().values():
        by_page[(c.doc_id, c.page)].append(c)

    args.out.mkdir(parents=True, exist_ok=True)
    fails, checked, sheet, docs = [], 0, [], {}
    for g in gold:
        key = (g["doc_id"], g["page"])
        on_page = by_page.get(key, [])
        if not on_page:
            print(f"{g['id']}  {key[0]} p{key[1]}: no chunks (not ingested) - skipped")
            sheet.append((g, None, None))
            continue
        doc = docs.setdefault(key[0], pymupdf.open(ROOT / "corpus" / f"{key[0]}.pdf"))
        page = doc[key[1] - 1]

        render = config.PAGES_DIR / Path(on_page[0].source_image).name
        from PIL import Image
        with Image.open(render) as im:
            dw, dh = im.width / SCALE - page.rect.width, im.height / SCALE - page.rect.height
        if abs(dw) > 1 or abs(dh) > 1:
            fails.append(f"{g['id']} render {render.name} off by ({dw:.1f}, {dh:.1f}) pt")

        worst = 1.0
        for c in on_page:
            r = check_chunk(page, c)
            checked += 1
            worst = min(worst, r)
            if r < args.min:
                fails.append(f"{g['id']} {c.chunk_id}: {r:.2f} of its text inside bbox")

        gist = set(tokens(g["answer_gist"]))
        best = max(on_page, key=lambda c: len(gist & set(tokens(c.text))))
        png = args.out / f"{g['id']}.png"
        png.write_bytes(crop_png(best, config.PAGES_DIR))
        sheet.append((g, best, png.name))
        print(f"{g['id']}  {key[0]} p{key[1]}: {len(on_page)} chunks, worst recall {worst:.2f}")

    rows = []
    for g, c, png in sheet:
        body = (f'<img src="{png}" alt="">' f"<p><code>{c.chunk_id}</code><br>{html.escape(c.text[:300])}</p>"
                if c else "<p><em>not ingested</em></p>")
        rows.append(f"<section><h2>{g['id']}: {html.escape(g['question'])}</h2>"
                    f"<p class=g>gist: {html.escape(g['answer_gist'])}</p>{body}</section>")
    (args.out / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Crop check</title><style>body{font:14px system-ui;"
        "max-width:900px;margin:auto;padding:16px}img{max-width:100%;border:1px solid #999}"
        ".g{color:#555}section{border-bottom:1px solid #ddd;padding:12px 0}</style>"
        + "".join(rows), encoding="utf-8")

    print(f"\n{checked} chunks on {sum(1 for _, c, _ in sheet if c)} gold pages; "
          f"{len(fails)} failures; contact sheet: {args.out / 'index.html'}")
    for f in fails:
        print("  FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
