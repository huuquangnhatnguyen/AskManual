"""Reading chunks.jsonl. Every consumer goes through here so the schema check runs once, in one place."""
from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path

from core import config
from ingest.schema import Chunk


def iter_chunks(path: Path | None = None) -> Iterator[Chunk]:
    with Path(path or config.CHUNKS_PATH).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield Chunk.model_validate_json(line)


def load_chunks(path: Path | None = None) -> dict[str, Chunk]:
    return {c.chunk_id: c for c in iter_chunks(path)}


@lru_cache(maxsize=4)
def chunk_store(path: str | None = None) -> dict[str, Chunk]:
    """Process-wide cached load — 35k chunks take a few seconds, so load once."""
    return load_chunks(Path(path) if path else None)
