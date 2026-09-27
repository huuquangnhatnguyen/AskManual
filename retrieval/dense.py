"""AS2.3 / AS3.1 — dense search over the Qdrant collection built by `python -m retrieval.index`."""
import atexit

from core import config
from retrieval.base import Hit


def qdrant_client():
    """The Qdrant server at QDRANT_URL, or the embedded on-disk store at QDRANT_PATH when it is empty."""
    from qdrant_client import QdrantClient
    if config.QDRANT_URL:
        return QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY, timeout=30)
    config.QDRANT_PATH.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(config.QDRANT_PATH))
    atexit.register(client.close)  # closing in __del__ at interpreter shutdown prints a traceback
    return client


class DenseRetriever:
    name = "dense"

    def __init__(self, collection: str | None = None, client=None):
        self.collection = collection or config.QDRANT_COLLECTION
        self.client = client or qdrant_client()

    def search(self, query: str, k: int = 5, product_family: str | None = None) -> list[Hit]:
        from qdrant_client import models

        from retrieval.embed import embed_query
        flt = None
        if product_family:
            flt = models.Filter(must=[models.FieldCondition(
                key="product_family", match=models.MatchAny(any=[product_family]))])
        points = self.client.query_points(
            self.collection, query=embed_query(query), limit=k, query_filter=flt, with_payload=True,
        ).points
        return [Hit(p.payload["chunk_id"], p.payload["doc_id"], p.payload["page"], p.score) for p in points]
