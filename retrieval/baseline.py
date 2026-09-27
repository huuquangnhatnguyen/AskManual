"""AS2.2 — naive baseline: the comparison column of the final results table.

Raw PDF text, 500-character blind chunks, dense only, no metadata filtering.
It must be *fair*: same embedding model as the real pipeline (retrieval.embed),
sensible overlap, nothing deliberately broken.

Needs its own units, because blind chunks aren't schema chunks: each keeps
(doc_id, page) so recall@5 can be scored, and its chunk_id is synthetic
("baseline_<doc>_p<page>_<n>") — it never reaches /evidence.

Scanned manual: the baseline reads the same corpus/*.pdf the pipeline ingests, so the
flattened scan contributes no text to either side until AS1.4 adds OCR. Same inputs,
different method: that is the comparison the table claims.

Build with `python -m retrieval.baseline` (writes index/baseline.npz; embeds every page of
every manual, ~20-30 min on CPU). Not built on first use, so a test can't trigger it.
"""
from pathlib import Path

import numpy as np

from core import config
from retrieval.base import Hit

CHUNK_CHARS = 500
OVERLAP = 100
CACHE = config.ROOT / "index" / "baseline.npz"


def blind_chunks(corpus: Path) -> list[tuple[str, str, int, str]]:
    """(chunk_id, doc_id, page, text) for every 500-char window, per page so the page is known."""
    import pymupdf
    out = []
    for pdf in sorted(corpus.glob("*.pdf")):
        doc_id = pdf.stem
        with pymupdf.open(pdf) as doc:
            for pno, page in enumerate(doc, start=1):
                text = " ".join(page.get_text().split())
                for n, start in enumerate(range(0, max(len(text) - OVERLAP, 1), CHUNK_CHARS - OVERLAP)):
                    window = text[start:start + CHUNK_CHARS]
                    if window.strip():
                        out.append((f"baseline_{doc_id}_p{pno}_{n}", doc_id, pno, window))
    return out


def build(corpus: Path, cache: Path = CACHE) -> int:
    from retrieval.embed import embed_documents
    chunks = blind_chunks(corpus)
    vectors = np.asarray(embed_documents(t for *_, t in chunks), dtype=np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, vectors=vectors,
             chunk_ids=np.array([c[0] for c in chunks]),
             doc_ids=np.array([c[1] for c in chunks]),
             pages=np.array([c[2] for c in chunks]))
    return len(chunks)


class BaselineRetriever:
    name = "baseline"

    def __init__(self, cache: Path = CACHE):
        if not cache.exists():
            raise FileNotFoundError(f"{cache} missing: build it with `python -m retrieval.baseline`")
        data = np.load(cache)
        self.vectors = data["vectors"]
        self.chunk_ids, self.doc_ids, self.pages = data["chunk_ids"], data["doc_ids"], data["pages"]

    def search(self, query: str, k: int = 5, product_family: str | None = None) -> list[Hit]:
        # product_family is ignored by design: "no metadata filtering".
        from retrieval.embed import embed_query
        q = np.asarray(embed_query(query), dtype=np.float32)
        scores = self.vectors @ (q / np.linalg.norm(q))
        top = np.argsort(-scores)[:k]
        return [Hit(str(self.chunk_ids[i]), str(self.doc_ids[i]), int(self.pages[i]), float(scores[i]))
                for i in top]


if __name__ == "__main__":
    print(f"baseline chunks: {build(config.ROOT / 'corpus')}")
