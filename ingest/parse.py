"""AS1.1: one PDF -> schema chunks. Prose and headings from text blocks, rows from tables.

Layout rules, all measured on this corpus rather than assumed:
- Running headers/footers are text in the top or bottom 7% of the page that
  recurs (digits masked) on 3+ pages. Chapter-level running heads ("Fault
  tracing 555") only recur within one chapter, so the bar has to be that low.
- Headings are bold blocks with real words, either set larger than body text
  or short and unpunctuated. Size alone misleads: parameter tables make 7 pt
  the most common size in the firmware manuals, against 8.9 pt body text.
  The outline (sections.py) gives section *structure*; this only decides
  chunk_type.
- The manuals' own contents pages (dot leaders) are dropped.
- Text inside a detected table is emitted only as table rows, never twice.
- Very short fragments (terminal labels on diagrams, lone bullets) are not
  retrievable on their own and are dropped; figures are AS1.3's job.
- Pages with no text layer produce nothing here — AS1.3 / AS1.4.
"""
import re
from collections import Counter
from dataclasses import dataclass

import pymupdf

from ingest.schema import Chunk
from ingest.sections import SectionIndex
from ingest.tables import cut_header, not_a_table, table_rows, usable
from ingest.text import clean, codes_in_prose

MARGIN = 0.07
MAX_CHARS = 1500      # a block longer than this is split on line boundaries
PIECE_CHARS = 900
MIN_CHARS = 8
BOLD = 16             # PyMuPDF span flag
DOT_LEADER = re.compile(r"(?:\. ?){6,}")


@dataclass
class Piece:
    rect: pymupdf.Rect
    text: str
    kind: str
    codes: list[str]


def _furniture_key(text: str) -> str:
    return re.sub(r"\d+", "#", clean(text)).lower()


def survey(doc: pymupdf.Document) -> tuple[set[str], float]:
    """Pre-pass: recurring header/footer strings, and the body font size (char-weighted mode)."""
    seen: Counter = Counter()
    sizes: Counter = Counter()
    for i, page in enumerate(doc):
        H = page.rect.height
        keys = set()
        for b in page.get_text("blocks"):
            if b[6] == 0 and (b[3] < H * MARGIN or b[1] > H * (1 - MARGIN)):
                keys.add(_furniture_key(b[4]))
        seen.update(keys)
        if i % 4 == 0:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for s in line["spans"]:
                        sizes[round(s["size"], 1)] += len(s["text"].strip())
    threshold = 3
    furniture = {k for k, n in seen.items() if n >= threshold and k}
    body = sizes.most_common(1)[0][0] if sizes else 10.0
    return furniture, body


def _block_pieces(block: dict, body: float) -> list[Piece]:
    lines = [ln for ln in block["lines"] if any(s["text"].strip() for s in ln["spans"])]
    if not lines:
        return []
    raw = "\n".join("".join(s["text"] for s in ln["spans"]) for ln in lines)
    text = clean(raw)
    spans = [s for ln in lines for s in ln["spans"] if s["text"].strip()]
    chars = sum(len(s["text"].strip()) for s in spans) or 1
    size = sum(s["size"] * len(s["text"].strip()) for s in spans) / chars
    bold = sum(len(s["text"].strip()) for s in spans if s["flags"] & BOLD) / chars

    if DOT_LEADER.search(text):
        return []
    is_heading = (
        bold > 0.8 and len(text) <= 120 and len(lines) <= 3 and re.search(r"[A-Za-z]{3}", text)
        and not text.startswith("•")
        and (size >= body * 1.2 or (len(text) <= 80 and not text.endswith((".", ":", ";", ","))))
    )
    if is_heading:
        return [Piece(pymupdf.Rect(block["bbox"]), text, "heading", [])]
    if len(text) < MIN_CHARS or len(re.findall(r"[A-Za-z]{2,}", text)) < 2:
        return []
    if len(text) <= MAX_CHARS:
        return [Piece(pymupdf.Rect(block["bbox"]), text, "prose", codes_in_prose(text))]

    pieces, buf, rect = [], [], None
    for ln in lines:
        t = "".join(s["text"] for s in ln["spans"])
        buf.append(t)
        rect = pymupdf.Rect(ln["bbox"]) if rect is None else rect | pymupdf.Rect(ln["bbox"])
        if sum(len(x) for x in buf) >= PIECE_CHARS:
            pieces.append((rect, clean("\n".join(buf))))
            buf, rect = [], None
    if buf:
        pieces.append((rect, clean("\n".join(buf))))
    return [Piece(r, t, "prose", codes_in_prose(t)) for r, t in pieces if t]


def _words_in(words: list[tuple], rect: pymupdf.Rect) -> str:
    """Page words centred in `rect`, in reading order: text a clipped table cell cut in half, whole."""
    inside = [w for w in words if rect.contains(pymupdf.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2))]
    inside.sort(key=lambda w: (w[5], w[6], w[7]))  # block, line, word
    return clean(" ".join(w[4] for w in inside))


def _inside(rect: pymupdf.Rect, zones: list[pymupdf.Rect]) -> bool:
    area = rect.get_area() or 1.0
    return any((rect & z).get_area() / area > 0.5 for z in zones)


def parse_page(page: pymupdf.Page, furniture: set[str], body: float, carry: str | None
               ) -> tuple[list[Piece], str | None]:
    words = page.get_text("words")
    tables = [t for t in page.find_tables().tables if usable(t) and not not_a_table(t, words)]
    zones = [pymupdf.Rect(t.bbox) for t in tables]
    unlabelled = frozenset(i for i, t in enumerate(tables) if cut_header(t, words))
    rows, carry = table_rows(tables, carry, unlabelled)
    pieces = [Piece(r.rect, r.text, "table_row", r.fault_codes) for r in rows if " | " in r.text]
    # A clipped header's labels are dropped from the rows; its text is kept whole, read from the page.
    for i in unlabelled:
        rect = pymupdf.Rect(tables[i].rows[0].bbox)
        text = _words_in(words, rect)
        if text:
            pieces.append(Piece(rect, text, "prose", codes_in_prose(text)))
    # A one-cell "row" isn't a row; keep its text as prose.
    pieces += [Piece(r.rect, r.text, "prose", codes_in_prose(r.text)) for r in rows if " | " not in r.text]

    H = page.rect.height
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        rect = pymupdf.Rect(block["bbox"])
        if zones and _inside(rect, zones):
            continue
        if rect.y1 < H * MARGIN or rect.y0 > H * (1 - MARGIN):
            raw = "\n".join("".join(s["text"] for s in ln["spans"]) for ln in block["lines"])
            if _furniture_key(raw) in furniture or not re.search(r"[A-Za-z]{3}", raw):
                continue
        pieces.extend(_block_pieces(block, body))
    pieces.sort(key=lambda p: (round(p.rect.y0), p.rect.x0))
    return pieces, carry


def to_bbox(rect: pymupdf.Rect, W: float, H: float) -> tuple[float, float, float, float] | None:
    """PyMuPDF top-left Rect -> schema bottom-left bbox, clamped to the page. None if degenerate."""
    x0, x1 = max(0.0, rect.x0), min(W, rect.x1)
    y0, y1 = max(0.0, H - rect.y1), min(H, H - rect.y0)
    if x1 - x0 < 0.5 or y1 - y0 < 0.5:
        return None
    return (round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1))


def parse_document(doc: pymupdf.Document, doc_id: str, families: list[str], stats: Counter):
    """Yield (page_no, [Chunk]) for every page."""
    furniture, body = survey(doc)
    sections = SectionIndex(doc)
    carry = None
    for page in doc:
        page_no = page.number + 1
        if page.rotation:
            raise ValueError(f"{doc_id} p{page_no} is rotated; schema.md requires the unrotated-space path")
        if not page.get_text().strip():
            stats["pages_no_text"] += 1
            yield page_no, []
            continue
        W, H = page.rect.width, page.rect.height
        pieces, carry = parse_page(page, furniture, body, carry)
        chunks = []
        for p in pieces:
            bbox = to_bbox(p.rect, W, H)
            if bbox is None:
                stats["dropped_degenerate"] += 1
                continue
            sec_id, sec_title = sections.at(page_no, bbox[3])
            chunk = Chunk(
                chunk_id=f"{doc_id}_p{page_no}_c{len(chunks):03d}",
                doc_id=doc_id,
                product_family=families,
                page=page_no,
                bbox=bbox,
                chunk_type=p.kind,
                text=p.text,
                parent_section_id=sec_id,
                parent_section_title=sec_title,
                fault_codes=p.codes,
                source_image=f"pages/{doc_id}_p{page_no:04d}.png",
            )
            chunk.check_page_bounds(W, H)
            chunks.append(chunk)
            stats[p.kind] += 1
        yield page_no, chunks
