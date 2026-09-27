"""Product family named in the question text, used to scope retrieval when the caller gave none.

M5 was to read the family off a nameplate photo; that was cut. The question itself often
names the drive ("ACS580-01 frame R1"), and a question about an ACS580 answered from the
ACS880 manual is wrong even when the words match.

Scopes only when the question names exactly one family the corpus knows. Two families
("swapping an ACS550 for an ACS580") is a cross-manual question: searching both is right.
"""
import re
from functools import cache

from core.chunks import chunk_store

FAMILY = re.compile(r"\b(ac[sq])\s*-?\s*(\d{3})", re.IGNORECASE)


@cache
def known_families() -> frozenset[str]:
    return frozenset(f for c in chunk_store().values() for f in c.product_family)


def named_families(query: str) -> set[str]:
    return {f"{a}{n}".upper() for a, n in FAMILY.findall(query)}


def infer_family(query: str, known: frozenset[str] | None = None) -> str | None:
    named = named_families(query)
    if len(named) != 1:
        return None
    (family,) = named
    return family if family in (known if known is not None else known_families()) else None
