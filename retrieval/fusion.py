"""AS3.1 — reciprocal rank fusion of dense + BM25 + the exact fault-code lane (retrieval/codes.py).

    score(d) = sum over retrievers i that returned d of 1 / (k + rank_i(d)),   k = 60, rank from 1

Ranks in, no score normalisation: BM25 and cosine values are never compared directly.
"""
from dataclasses import replace

from retrieval.base import Hit, Retriever

RRF_K = 60


def rrf(rankings: list[list[Hit]], k: int = RRF_K) -> list[Hit]:
    """Fuse ranked lists into one, best first. Each output Hit's `score` is its RRF score.
    Ties break by chunk_id so a run is deterministic."""
    scores: dict[str, float] = {}
    first: dict[str, Hit] = {}  # keeps doc_id/page; every retriever reports the same ones for a chunk
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1 / (k + rank)
            first.setdefault(hit.chunk_id, hit)
    order = sorted(scores, key=lambda cid: (-scores[cid], cid))
    return [replace(first[cid], score=scores[cid]) for cid in order]


class FusedRetriever:
    name = "fused"

    def __init__(self, retrievers: list[Retriever] | None = None, depth: int = 50, scope: bool = True):
        from retrieval import registry
        self.retrievers = retrievers or [registry.get(n) for n in ("dense", "bm25", "codes")]
        self.depth = depth  # how deep each input list goes before fusing
        self.scope = scope  # infer product_family from the question when the caller gives none

    def search(self, query: str, k: int = 5, product_family: str | None = None) -> list[Hit]:
        if product_family is None and self.scope:
            from retrieval.scope import infer_family
            product_family = infer_family(query)
        rankings = [r.search(query, self.depth, product_family) for r in self.retrievers]
        return rrf(rankings)[:k]
