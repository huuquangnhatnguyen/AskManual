"""Metric definitions, fixed in AS2.1 and not renegotiated later.

recall@k           fraction of gold questions whose known source page is among the top-k hits.
                   A page matches on (doc_id, page); `also_supported_by` pages count too.
citation accuracy  fraction of produced answers whose cited pages actually contain the answer.
"""
from retrieval.base import Hit


def gold_pages(gold: dict) -> set[tuple[str, int]]:
    pages = {(gold["doc_id"], gold["page"])}
    pages |= {(p["doc_id"], p["page"]) for p in gold.get("also_supported_by", [])}
    return pages


def hit_at_k(hits: list[Hit], gold: dict, k: int = 5) -> bool:
    want = gold_pages(gold)
    return any((h.doc_id, h.page) in want for h in hits[:k])


def first_rank(hits: list[Hit], gold: dict) -> int | None:
    """1-based rank of the first hit on a gold page, or None — for the per-question miss report."""
    want = gold_pages(gold)
    return next((i for i, h in enumerate(hits, 1) if (h.doc_id, h.page) in want), None)


def citation_correct(cited_pages: set[tuple[str, int]], gold: dict) -> bool:
    """An answer's citations are correct if any cited page is a gold page.
    Used once AS4.1 produces answers (`python -m eval.run --answers`)."""
    return bool(cited_pages & gold_pages(gold))
