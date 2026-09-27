"""Every environment key the app reads. `.env.example` mirrors this file.

One module for all packages, so ingest, retrieval, generation, eval and api
never disagree about where chunks live or which model runs.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

# Backing services
DATABASE_URL = os.environ.get("DATABASE_URL", "")
QDRANT_URL = os.environ.get("QDRANT_URL", "")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY") or None
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "chunks")
# Used only when QDRANT_URL is empty: qdrant-client's embedded mode, no server needed.
# One process at a time may open it, so the API and an eval run can't share it concurrently.
QDRANT_PATH = Path(os.environ.get("QDRANT_PATH") or ROOT / "index" / "qdrant")

# Ingest artifacts — the one file every index is built from (AS2.3)
CHUNKS_PATH = Path(os.environ.get("CHUNKS_PATH", ROOT / "chunks.jsonl"))
PAGES_DIR = Path(os.environ.get("PAGES_DIR", ROOT / "pages"))
BM25_PATH = Path(os.environ.get("BM25_PATH", ROOT / "index" / "bm25.pkl"))

# Retrieval
EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")  # local ONNX, no key
RETRIEVER = os.environ.get("RETRIEVER", "fused")                       # registry name /ask uses
REFUSAL_THRESHOLD = float(os.environ.get("REFUSAL_THRESHOLD", "0"))    # AS3.2 calibrates this

# Generation. The SDK reads ANTHROPIC_API_KEY itself; it is named here for .env.example.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-opus-5")
GENERATION_TIMEOUT = float(os.environ.get("GENERATION_TIMEOUT", "45"))  # seconds

# "fixture" serves api/fixtures (AS0.5); "real" runs retrieve -> generate (AS4.3).
PIPELINE = os.environ.get("PIPELINE", "fixture")
