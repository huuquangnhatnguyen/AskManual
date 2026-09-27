"""The one embedding model, shared by the baseline (AS2.2) and the real index (AS2.3) —
the comparison is only fair if both use the same one.

fastembed runs locally on ONNX: no key, no torch, and a judge rebuilding the
index needs nothing but this package (AS8.5). First call downloads the model.
"""
from collections.abc import Iterable
from functools import cache

from core import config


@cache
def _model():
    from fastembed import TextEmbedding
    return TextEmbedding(config.EMBED_MODEL)


def dim() -> int:
    return len(embed_query("probe"))


def embed_documents(texts: Iterable[str], batch_size: int = 64) -> list[list[float]]:
    return [v.tolist() for v in _model().embed(list(texts), batch_size=batch_size)]


def embed_query(text: str) -> list[float]:
    # bge models expect the query-side instruction; fastembed's query_embed adds it.
    return next(iter(_model().query_embed(text))).tolist()
