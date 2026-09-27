"""AskManual API. Run: uvicorn api.main:app

PIPELINE=fixture (default): /ask and /evidence serve api/fixtures/, as in AS0.5.
PIPELINE=real: /ask runs api/pipeline.py and /evidence crops from chunks.jsonl + pages/.
The contract (api/models.py, api/CONTRACT.md) is the same in both modes.
"""
import asyncio
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import TypeAdapter

from api import config, site
from api.evidence import crop_png, load_chunks, load_json
from api.models import AskRequest, AskResponse, Health, Identified, Probe
from generation.llm import GenerationError, GenerationTimeout

HERE = Path(__file__).parent
FIXTURES = HERE / "fixtures"
CHUNK_ID = re.compile(r"^[a-z0-9_]+$")
MAX_UPLOAD = 15 * 1024 * 1024

app = FastAPI(title="AskManual", version="0.1.0")
templates = Jinja2Templates(directory=HERE / "templates")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

_ask = TypeAdapter(AskResponse)
REAL = config.PIPELINE == "real"
if REAL:
    from api.pipeline import answer_question
    from core.chunks import chunk_store
    CHUNKS = chunk_store()
    PAGES = config.PAGES_DIR
else:
    CHUNKS = load_chunks(FIXTURES / "chunks.jsonl")
    PAGES = FIXTURES / "pages"
ANSWER = _ask.validate_python(load_json(FIXTURES / "answer.json"))
REFUSAL = _ask.validate_python(load_json(FIXTURES / "refusal.json"))


# ---- Pages. Thin: data comes from api/site.py, markup from templates/, behaviour from static/. ----

EXAMPLES = [
    ("Fault code", "ACS580 is showing fault 2330. What is it and what should I check first?"),
    ("Wiring", "What is the tightening torque for the PE ground lug on an ACS580-01 frame R1?"),
    ("Derating", "How much do I derate an ACS580 installed at 2500 m altitude?"),
    ("I/O", "What is the contact rating of the relay outputs on an ACS880-01 control unit?"),
    ("Out of scope", "How do I reset a Siemens S7-1200 PLC to factory defaults?"),
]


# Changes whenever a static file does, so a phone never runs new HTML against a cached old CSS/JS.
ASSET_VERSION = str(max(int(p.stat().st_mtime) for p in (HERE / "static").iterdir()))


def page(request: Request, name: str, active: str, **context):
    return templates.TemplateResponse(request, f"{name}.html",
                                      {"active": active, "asset_version": ASSET_VERSION, **context})


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request):
    return page(request, "ask", "ask", examples=EXAMPLES)


@app.get("/answer", response_class=HTMLResponse, include_in_schema=False)
def answer_page(request: Request, q: str = "", family: str = ""):
    question = q.strip()[:1000]
    if not question:
        return RedirectResponse("/", status_code=303)
    # Stub knobs (PIPELINE=fixture): /answer?q=..&fixture=refusal or &delay=3 pass through to /ask.
    knobs = urlencode({k: v for k, v in request.query_params.items() if k in ("fixture", "delay")})
    return page(request, "answer", "ask", question=question, family=family,
                ask={"question": question, "product_family": family or None, "query": knobs},
                titles={d: t for d, t, *_ in site.MANUALS})


@app.get("/manuals", response_class=HTMLResponse, include_in_schema=False)
def manuals_page(request: Request):
    return page(request, "manuals", "manuals", manuals=site.manuals())


@app.get("/results", response_class=HTMLResponse, include_in_schema=False)
def results_page(request: Request):
    return page(request, "results", "results", results=site.results())


@app.get("/about", response_class=HTMLResponse, include_in_schema=False)
def about_page(request: Request):
    return page(request, "about", "about")


@app.post("/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    fixture: Literal["answer", "refusal"] = Query("answer", description="PIPELINE=fixture only"),
    delay: float = Query(0.0, ge=0, le=10, description="PIPELINE=fixture only — simulate a slow generation call"),
):
    if REAL:
        try:
            return await asyncio.wait_for(
                run_in_threadpool(answer_question, body.question, body.product_family),
                timeout=config.GENERATION_TIMEOUT + 5)
        except (asyncio.TimeoutError, GenerationTimeout):
            raise HTTPException(504, "generation timed out")
        except GenerationError:
            raise HTTPException(502, "generation failed")
    if delay:
        await asyncio.sleep(delay)
    return REFUSAL if fixture == "refusal" else ANSWER


@app.post("/identify", response_model=Identified)
async def identify(image: UploadFile):
    if not (image.content_type or "").startswith("image/"):
        raise HTTPException(415, "upload must be an image")
    data = await image.read(MAX_UPLOAD + 1)
    if not data:
        raise HTTPException(422, "empty upload")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "image larger than 15 MB")
    return Identified(model_number="ACS580-01-12A7-4", fault_code="2330")


@app.get("/evidence/{chunk_id}", responses={200: {"content": {"image/png": {}}}})
def evidence(chunk_id: str):
    chunk = CHUNKS.get(chunk_id) if CHUNK_ID.match(chunk_id) else None
    if chunk is None:
        raise HTTPException(404, "unknown chunk_id")
    return Response(crop_png(chunk, PAGES), media_type="image/png",
                    headers={"Cache-Control": "public, max-age=86400"})


async def _probe_qdrant() -> Probe:
    if not config.QDRANT_URL:
        # Embedded mode (retrieval/dense.py): no server to ask. Opening the store here would
        # contend for its lock with the retriever, so report whether it has been built.
        built = (config.QDRANT_PATH / "collection").exists()
        return Probe(ok=built, detail=f"embedded at {config.QDRANT_PATH.name}" if built else "embedded store not built")
    headers = {"api-key": config.QDRANT_API_KEY} if config.QDRANT_API_KEY else {}
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(config.QDRANT_URL.rstrip("/") + "/readyz", headers=headers)
        return Probe(ok=r.is_success, detail=f"HTTP {r.status_code}")
    except httpx.HTTPError as e:
        return Probe(ok=False, detail=type(e).__name__)


def _probe_postgres() -> Probe:
    if not config.DATABASE_URL:
        return Probe(ok=False, detail="DATABASE_URL not set")
    try:
        import psycopg
        with psycopg.connect(config.DATABASE_URL, connect_timeout=3) as conn:
            conn.execute("SELECT 1")
        return Probe(ok=True, detail="SELECT 1")
    except Exception as e:  # report the kind of failure, never the connection string
        return Probe(ok=False, detail=type(e).__name__)


@app.get("/health", response_model=Health)
async def health():
    qdrant, postgres = await asyncio.gather(_probe_qdrant(), run_in_threadpool(_probe_postgres))
    return Health(status="ok" if qdrant.ok and postgres.ok else "degraded", qdrant=qdrant, postgres=postgres)
