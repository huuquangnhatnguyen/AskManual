"""AS1.2: one chunk per table row, from PyMuPDF's ruled-table finder.

Fault and warning tables have a `Code (hex)` column. Inside a fault entry,
aux-code sub-rows leave that column empty and belong to the fault above them,
so they are merged into its row rather than emitted as faults of their own
(corpus.md, "Aux codes share the code column"). An aux run that starts at the
top of a page continues the last code of the previous page; it is emitted as
its own row, labelled with that code, since a chunk cannot span two pages.
"""
import re
from dataclasses import dataclass, field

import pymupdf

from ingest.text import FAULT_CODE, clean

_GENERIC_HEADER = re.compile(r"^Col\d+$")


@dataclass
class Row:
    text: str
    rect: pymupdf.Rect
    fault_codes: list[str] = field(default_factory=list)


def _cells(row: list[str | None]) -> list[str]:
    return [clean(c or "") for c in row]


def _join(headers: list[str], cells: list[str]) -> str:
    parts = []
    for h, c in zip(headers, cells):
        if c:
            parts.append(f"{h}: {c}" if h and h != c else c)
    return " | ".join(parts)


def _row_rect(row) -> pymupdf.Rect:
    """Union of the row's real cells. The row's own bbox can span several visual
    rows when a column has vertically merged cells, which makes a loose crop."""
    cells = [pymupdf.Rect(c) for c in row.cells if c]
    if not cells:
        return pymupdf.Rect(row.bbox)
    rect = cells[0]
    for c in cells[1:]:
        rect |= c
    return rect


def usable(table) -> bool:
    """Reject layout frames the finder mistakes for tables: need 2+ columns with 2+ filled cells in some row."""
    if table.col_count < 2:
        return False
    return any(sum(1 for c in row if c and c.strip()) >= 2 for row in table.extract())


STRADDLE_MAX = 1  # words a real table may push across a cell edge (an overflowing part number, say)


def cuts_words(table, words: list[tuple]) -> bool:
    """True when the finder's cell edges run through words, i.e. it split text that isn't tabular.

    A ruled table keeps every word inside its cell. When a diagram line or a text frame is read as
    a column rule, words straddle it and each cell's text is clipped at the edge ("nsulated",
    "rive's", "WA … RNING"). About 10% of the tables the finder accepts in this corpus do this:
    diagram callouts, framed WARNING boxes, and tables with a phantom column. Rejected tables fall
    through to the prose path, which reads the same text intact. `words` is page.get_text("words").
    """
    x0, x1 = table.bbox[0] + 1, table.bbox[2] - 1
    n = 0
    for row in table.rows:
        for cell in row.cells:
            if not cell:
                continue
            c = pymupdf.Rect(cell)
            edges = [x for x in (c.x0, c.x1) if x0 < x < x1]  # interior edges only
            for w in words:
                if c.y0 <= (w[1] + w[3]) / 2 <= c.y1 and any(w[0] < x - 1.5 and w[2] > x + 1.5 for x in edges):
                    n += 1
                    if n > STRADDLE_MAX:
                        return True
    return False


def table_rows(tables: list, carry: str | None) -> tuple[list[Row], str | None]:
    """Rows of every usable table on a page. `carry` is the last fault code seen on the previous page."""
    out: list[Row] = []
    for t in tables:
        raw = [h or "" for h in t.header.names]
        has_header = not all(_GENERIC_HEADER.match(h) for h in raw if h)
        headers = [clean(h) for h in raw] if has_header else [""] * t.col_count
        code_col = next((i for i, h in enumerate(headers) if h.lower().startswith("code")), None)

        data = t.extract()
        rects = [_row_rect(r) for r in t.rows]
        start = 1 if has_header and not t.header.external else 0
        current: Row | None = None
        for cells, rect in zip(map(_cells, data[start:]), rects[start:]):
            if not any(cells):
                continue
            text = _join(headers, cells)
            if code_col is not None and not cells[code_col]:
                if current is not None:          # aux-code sub-row: belongs to the fault above
                    current.text += " | " + text
                    current.rect |= rect
                    continue
                if carry:                         # aux rows continuing from the previous page
                    current = Row(f"{headers[code_col] or 'Code'}: {carry} (continued) | {text}", rect)
                    out.append(current)
                    continue
            codes = []
            if code_col is not None and FAULT_CODE.match(cells[code_col].upper()):
                codes = [cells[code_col].upper()]
                carry = codes[0]
            current = Row(text, rect, codes)
            out.append(current)
    return out, carry
