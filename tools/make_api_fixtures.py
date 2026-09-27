"""Build the AS0.5 API fixtures from two real corpus pages.

Writes, under api/fixtures/:
  chunks.jsonl                          schema-valid chunks (ingest/schema.py)
  pages/acs580_firmware_manual_p0553.png  150 dpi page render — fault 2330 row
  pages/acs580_firmware_manual_p0535.png  150 dpi page render — safety WARNING

The stubbed /ask answer (api/fixtures/answer.json) cites these chunk ids, and
/evidence crops from these renders with the same code AS4.3 uses on pages/.

Run:  python tools/make_api_fixtures.py
Needs corpus/acs580_firmware_manual.pdf. Output is committed, so the deployed
app never needs the corpus.
"""
import json
import sys
from pathlib import Path

import pymupdf

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ingest.schema import Chunk  # noqa: E402
from ingest.sections import SectionIndex  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "api" / "fixtures"
DOC = "acs580_firmware_manual"
DPI = 150


def schema_bbox(rect: pymupdf.Rect, height: float) -> list[float]:
    """PyMuPDF top-left Rect -> schema.md bottom-left [x0, y0, x1, y1]."""
    return [round(rect.x0, 1), round(height - rect.y1, 1), round(rect.x1, 1), round(height - rect.y0, 1)]


def flat(s: str) -> str:
    return " ".join(s.split())


def main() -> int:
    doc = pymupdf.open(ROOT / "corpus" / f"{DOC}.pdf")
    sections = SectionIndex(doc)
    (OUT / "pages").mkdir(parents=True, exist_ok=True)

    # (page, chunk index, chunk_type, text the chunk's first block starts with, fault codes)
    specs = [
        (553, 1, "table_row", "2330", ["2330"]),
        (553, 12, "table_row", "2381", ["2381"]),
        (535, 4, "prose", "WARNING!", []),
    ]
    chunks = []
    for page_no, n, ctype, anchor, codes in specs:
        page = doc[page_no - 1]
        H = page.rect.height
        blocks = page.get_text("blocks")
        if ctype == "table_row":
            # The row = the block starting with the code plus every block on the same top line.
            head = next(b for b in blocks if b[4].startswith(anchor + "\n"))
            cells = sorted((b for b in blocks if abs(b[1] - head[1]) < 1.0), key=lambda b: b[0])
            first = cells[0][4].split("\n", 2)  # code, name, cause...
            parts = [first[0], first[1], flat(first[2])] + [flat(c[4]) for c in cells[1:]]
            text = " | ".join(p for p in parts if p)
            rect = pymupdf.Rect(cells[0][:4])
            for c in cells[1:]:
                rect |= pymupdf.Rect(c[:4])
        else:
            b = next(b for b in blocks if b[4].startswith(anchor))
            text, rect = flat(b[4]), pymupdf.Rect(b[:4])
        bbox = schema_bbox(rect, H)
        sec_id, sec_title = sections.at(page_no, bbox[3])
        chunk = Chunk(
            chunk_id=f"{DOC}_p{page_no}_c{n:03d}",
            doc_id=DOC,
            product_family=["ACS580"],
            page=page_no,
            bbox=bbox,
            chunk_type=ctype,
            text=text,
            parent_section_id=sec_id,
            parent_section_title=sec_title,
            fault_codes=codes,
            source_image=f"pages/{DOC}_p{page_no:04d}.png",
        )
        chunk.check_page_bounds(page.rect.width, H)
        chunks.append(chunk)

    for page_no in sorted({c.page for c in chunks}):
        pix = doc[page_no - 1].get_pixmap(dpi=DPI)
        pix.save(OUT / "pages" / f"{DOC}_p{page_no:04d}.png")

    with (OUT / "chunks.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for c in chunks:
            f.write(c.model_dump_json() + "\n")
            print(c.chunk_id, c.bbox, c.parent_section_id, c.parent_section_title, "|", c.text[:70])
    return 0


if __name__ == "__main__":
    sys.exit(main())
