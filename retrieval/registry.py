"""Retrievers by name. `python -m eval.run --retriever <name>` and RETRIEVER=<name> both resolve here.

Entries are import paths, not objects, so asking for `keyword` never loads
fastembed or connects to Qdrant. To add a retriever: write the class, add a line.
"""
from functools import cache
from importlib import import_module

from retrieval.base import Retriever

REGISTRY: dict[str, str] = {
    "keyword":  "retrieval.keyword:KeywordRetriever",    # test double, token overlap — no services
    "baseline": "retrieval.baseline:BaselineRetriever",  # AS2.2
    "dense":    "retrieval.dense:DenseRetriever",        # AS2.3
    "bm25":     "retrieval.bm25:BM25Retriever",          # AS3.1
    "codes":    "retrieval.codes:CodeRetriever",         # AS3.1, exact fault-code lane
    "fused":    "retrieval.fusion:FusedRetriever",       # AS3.1
}


def names() -> list[str]:
    return sorted(REGISTRY)


@cache
def get(name: str) -> Retriever:
    """Build (once per process) and return the retriever registered as `name`."""
    try:
        module, attr = REGISTRY[name].split(":")
    except KeyError:
        raise KeyError(f"unknown retriever {name!r}; registered: {', '.join(names())}") from None
    return getattr(import_module(module), attr)()
