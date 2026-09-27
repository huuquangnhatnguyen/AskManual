"""The retriever contract. The harness, the confidence gate and /ask depend on this and nothing else."""
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Hit:
    """One retrieved chunk. `score` is retriever-native: cosine, BM25 or RRF — comparable only within one retriever."""
    chunk_id: str
    doc_id: str
    page: int
    score: float


@runtime_checkable
class Retriever(Protocol):
    name: str

    def search(self, query: str, k: int = 5, product_family: str | None = None) -> list[Hit]:
        """Top-k hits, best first. `product_family` (uppercase, e.g. "ACS580") restricts to chunks
        whose `product_family` list contains it; None searches everything."""
        ...
