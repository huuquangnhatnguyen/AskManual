"""Token-overlap retriever. Not a contender — a stand-in that needs no services and no index,
so the harness, the pipeline and the tests run end to end before AS2.2 lands."""
import re
from collections import Counter

from core.chunks import chunk_store
from ingest.schema import Chunk
from retrieval.base import Hit

TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


class KeywordRetriever:
    name = "keyword"

    def __init__(self, chunks: dict[str, Chunk] | None = None):
        self.chunks = list((chunks if chunks is not None else chunk_store()).values())
        self.bags = [Counter(tokens(c.text)) for c in self.chunks]

    def search(self, query: str, k: int = 5, product_family: str | None = None) -> list[Hit]:
        q = set(tokens(query))
        scored = []
        for chunk, bag in zip(self.chunks, self.bags):
            if product_family and product_family not in chunk.product_family:
                continue
            s = sum(1 for t in q if t in bag)
            if s:
                scored.append((s / len(q), chunk))
        scored.sort(key=lambda sc: -sc[0])
        return [Hit(c.chunk_id, c.doc_id, c.page, s) for s, c in scored[:k]]
