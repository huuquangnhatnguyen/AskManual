"""AS2.3 — build every index from one chunks.jsonl, so they cannot drift apart.

    python -m retrieval.index              # all three
    python -m retrieval.index --only bm25  # one
    python -m retrieval.index --check      # counts only, builds nothing

Done when all three counts match, and
    SELECT * FROM fault_codes WHERE code = '2330' AND product_family = 'ACS580'
returns exactly one row.
"""
import argparse
import pickle
import sys
import uuid
from pathlib import Path

from core import config
from core.chunks import iter_chunks
from ingest.schema import Chunk

SQL = Path(__file__).parent / "sql" / "fault_codes.sql"


def build_qdrant(chunks: list[Chunk], batch: int = 512) -> int:
    """(Re)create config.QDRANT_COLLECTION: one point per chunk, vector from retrieval.embed,
    payload {chunk_id, doc_id, page, chunk_type, product_family}. Returns points written.
    Point ids must be ints or UUIDs: uuid5 of chunk_id keeps re-runs idempotent.
    35k chunks: embed in batches and upsert in batches, or it runs out of memory."""
    from qdrant_client import models

    from retrieval.bm25 import index_text
    from retrieval.dense import qdrant_client
    from retrieval.embed import dim, embed_documents

    client = qdrant_client()
    if client.collection_exists(config.QDRANT_COLLECTION):
        client.delete_collection(config.QDRANT_COLLECTION)
    client.create_collection(config.QDRANT_COLLECTION, vectors_config=models.VectorParams(
        size=dim(), distance=models.Distance.COSINE))
    written = 0
    for start in range(0, len(chunks), batch):
        part = chunks[start:start + batch]
        vectors = embed_documents(index_text(c) for c in part)
        client.upsert(config.QDRANT_COLLECTION, points=[
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, c.chunk_id)), vector=v,
                payload={"chunk_id": c.chunk_id, "doc_id": c.doc_id, "page": c.page,
                         "chunk_type": c.chunk_type, "product_family": c.product_family})
            for c, v in zip(part, vectors)
        ])
        written += len(part)
        print(f"  qdrant {written}/{len(chunks)}", flush=True)
    return written


def build_bm25(chunks: list[Chunk], path: Path | None = None) -> int:
    """Pickle {"bm25": BM25Okapi, "meta": [(chunk_id, doc_id, page, product_family), ...]}
    to config.BM25_PATH (retrieval/bm25.py loads it). Returns documents indexed."""
    from rank_bm25 import BM25Okapi

    from retrieval.bm25 import index_text
    from retrieval.keyword import tokens

    path = Path(path or config.BM25_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "bm25": BM25Okapi([tokens(index_text(c)) for c in chunks]),
        "meta": [(c.chunk_id, c.doc_id, c.page, list(c.product_family)) for c in chunks],
    }
    with path.open("wb") as f:
        pickle.dump(data, f)
    return len(chunks)


def build_fault_codes(chunks: list[Chunk]) -> int:
    """Recreate the fault_codes table (retrieval/sql/fault_codes.sql) from table_row chunks
    with codes: one row per (code, product_family, chunk). Returns rows written."""
    raise NotImplementedError("AS2.3: build_fault_codes")


def count_qdrant() -> int | None:
    try:
        from retrieval.dense import qdrant_client
        return qdrant_client().count(config.QDRANT_COLLECTION, exact=True).count
    except Exception:
        return None


def count_bm25() -> int | None:
    if not config.BM25_PATH.exists():
        return None
    with config.BM25_PATH.open("rb") as f:
        return len(pickle.load(f)["meta"])


def count_fault_code_chunks() -> int | None:
    """Distinct chunks, not rows — a chunk in a multi-family doc writes one row per family."""
    try:
        import psycopg
        with psycopg.connect(config.DATABASE_URL, connect_timeout=5) as conn:
            return conn.execute("SELECT count(DISTINCT chunk_id) FROM fault_codes").fetchone()[0]
    except Exception:
        return None


BUILDERS = {"qdrant": build_qdrant, "bm25": build_bm25, "fault_codes": build_fault_codes}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", choices=sorted(BUILDERS), action="append")
    ap.add_argument("--check", action="store_true", help="report counts, build nothing")
    ap.add_argument("--chunks", type=Path, default=config.CHUNKS_PATH)
    args = ap.parse_args(argv)

    chunks = list(iter_chunks(args.chunks))
    if not args.check:
        for name in args.only or BUILDERS:
            print(f"built {name}: {BUILDERS[name](chunks)}")

    expect = {
        "qdrant": len(chunks),
        "bm25": len(chunks),
        "fault_codes": sum(1 for c in chunks if c.chunk_type == "table_row" and c.fault_codes),
    }
    got = {"qdrant": count_qdrant(), "bm25": count_bm25(), "fault_codes": count_fault_code_chunks()}
    print(f"\n{'index':12} {'expected':>9} {'actual':>9}")
    ok = True
    for name in BUILDERS:
        match = got[name] == expect[name]
        ok &= match
        print(f"{name:12} {expect[name]:>9} {str(got[name]):>9}  {'ok' if match else 'MISMATCH'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
