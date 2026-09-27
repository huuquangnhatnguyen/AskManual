"""AS3.1 — BM25 over the same chunks.jsonl as the dense index, loaded from config.BM25_PATH."""
import pickle
from pathlib import Path

import numpy as np

from core import config
from ingest.schema import Chunk
from retrieval.base import Hit
from retrieval.keyword import tokens  # [a-z0-9]+: fault codes like 2330 and a2b1 stay one token


def index_text(chunk: Chunk) -> str:
    """What both indexes see for a chunk. The section title rides along so a bare table row
    ("2330 Earth leakage ...") still matches a query that names its table ("fault messages")."""
    return f"{chunk.parent_section_title}\n{chunk.text}" if chunk.parent_section_title else chunk.text


class BM25Retriever:
    name = "bm25"

    def __init__(self, path: Path | None = None):
        with Path(path or config.BM25_PATH).open("rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]
        self.meta = data["meta"]  # [(chunk_id, doc_id, page, product_family), ...], in index order

    def search(self, query: str, k: int = 5, product_family: str | None = None) -> list[Hit]:
        scores = self.bm25.get_scores(tokens(query))
        hits = []
        for i in np.argsort(-scores):
            if scores[i] <= 0:  # sorted, so nothing after this matches a query term either
                break
            chunk_id, doc_id, page, families = self.meta[i]
            if product_family and product_family not in families:
                continue
            hits.append(Hit(chunk_id, doc_id, page, float(scores[i])))
            if len(hits) == k:
                break
        return hits
