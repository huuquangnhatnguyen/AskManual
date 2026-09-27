"""AS3.1 — exact fault-code lane, fused alongside dense and BM25.

BM25 alone buries the answer to "ACS580 fault 2330": the row that defines 2330 is ~200 tokens
against a median chunk of ~17, so length normalisation ranks shorter rows that share only
"fault" and "check" above it. An exact lookup on the chunk's `fault_codes` field has no such
problem, and RRF lets it vote without its scores meeting anyone else's.

This is the lookup the Postgres fault_codes table (retrieval/sql/fault_codes.sql) is for;
it reads chunks.jsonl directly so it needs no service and cannot drift from the other indexes.
"""
from collections import defaultdict

from core.chunks import chunk_store
from ingest.schema import Chunk
from retrieval.base import Hit
from retrieval.keyword import tokens


class CodeRetriever:
    name = "codes"

    def __init__(self, chunks: dict[str, Chunk] | None = None):
        chunks = chunks if chunks is not None else chunk_store()
        self.by_code: dict[str, list[Chunk]] = defaultdict(list)
        for c in chunks.values():
            if c.chunk_type == "table_row":
                for code in c.fault_codes:
                    self.by_code[code.lower()].append(c)
        self.families = {f.lower() for c in chunks.values() for f in c.product_family}

    def search(self, query: str, k: int = 5, product_family: str | None = None) -> list[Hit]:
        q = tokens(query)
        codes = [t for t in dict.fromkeys(q) if t in self.by_code]  # only codes the corpus defines
        if not codes:
            return []
        named = {t for t in q if t in self.families}  # "ACS580" in the question: prefer its rows
        matched: dict[str, tuple[int, Chunk]] = {}
        for code in codes:
            for c in self.by_code[code]:
                if product_family and product_family not in c.product_family:
                    continue
                n, _ = matched.get(c.chunk_id, (0, c))
                matched[c.chunk_id] = (n + 1, c)

        def rank(item: tuple[int, Chunk]):
            n, c = item
            return (-n, not named & {f.lower() for f in c.product_family}, c.chunk_id)

        ordered = sorted(matched.values(), key=rank)[:k]
        # Score = codes matched. Only the rank reaches RRF; the score is here for debugging.
        return [Hit(c.chunk_id, c.doc_id, c.page, float(n)) for n, c in ordered]
