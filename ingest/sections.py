"""parent_section_id / parent_section_title from the PDF outline, per schema.md."""
from bisect import bisect_right

import pymupdf


class SectionIndex:
    """Nearest TOC heading above a point in the document.

    Ids are ordinal paths ("9.7"): the outlines carry titles but no printed
    numbers, so entries are counted per level. Several headings can start on
    one page (acs580_firmware_manual p535 opens four), so lookup uses the
    heading's position on the page, not just its page. TOC `to` points are in
    PDF space (y up) — checked on two documents — the same space as bbox.
    """

    def __init__(self, doc: pymupdf.Document):
        entries = []
        counters: list[int] = []
        for level, title, page, dest in doc.get_toc(simple=False):
            counters = counters[:level]
            counters += [0] * (level - len(counters))
            counters[level - 1] += 1
            if page < 1:
                continue
            y = dest["to"].y if isinstance(dest, dict) and "to" in dest else float("inf")
            entries.append(((page, -y), ".".join(map(str, counters)), " ".join(title.split())))
        entries.sort(key=lambda e: e[0])
        self._keys = [e[0] for e in entries]
        self._vals = [(e[1], e[2]) for e in entries]

    def at(self, page: int, top: float) -> tuple[str | None, str | None]:
        """Section enclosing a chunk on 1-based `page` whose bbox top (PDF y1) is `top`."""
        i = bisect_right(self._keys, (page, -top))
        return self._vals[i - 1] if i else (None, None)
