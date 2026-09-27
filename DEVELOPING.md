# Developing AskManual

How to get running, where things plug in, and what's left. `MILESTONES.md` says *what* each
task must deliver; this file says *where in the code* it goes.

## Setup

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows; source .venv/bin/activate elsewhere
pip install -e ".[dev]"
cp .env.example .env                                # fill DATABASE_URL, QDRANT_URL, POSTGRES_PASSWORD
docker compose up -d qdrant postgres                # optional: QDRANT_URL empty = embedded Qdrant
pytest                                              # green = passes + "pending: ASx.y" skips
```

`corpus/`, `pages/` and `chunks.jsonl` aren't in git. Rebuild them with
`python -m ingest.run corpus/`, or copy them from someone who has them.

## Commands

| Does | Command |
|---|---|
| Run the app (fixtures) | `uvicorn api.main:app --reload` then http://localhost:8000 |
| Run the app (real pipeline) | `PIPELINE=real uvicorn api.main:app` |
| Ingest | `python -m ingest.run corpus/` |
| Build all indexes | `python -m retrieval.index` (`--only bm25`, `--check`). Empty `QDRANT_URL` = embedded Qdrant, no Docker |
| Build the baseline index | `python -m retrieval.baseline` (~20-30 min, writes `index/baseline.npz`) |
| Score a retriever | `python -m eval.run --retriever <name> [--misses] [--answers]` |
| Calibrate refusal | `python -m eval.calibrate --retriever fused` |
| Tests | `pytest` / `pytest tests/test_fusion.py -rs` |

## How it fits together

```
corpus/*.pdf ──ingest──> chunks.jsonl + pages/*.png          (M1, done except figures + OCR)
                              │
               retrieval.index│ builds all three from the one file
                  ┌───────────┼──────────────┐
               Qdrant       BM25 pickle    Postgres fault_codes
                  │           │
          DenseRetriever  BM25Retriever
                  └──── rrf ──┘ FusedRetriever                 (retrieval/)
                          │
   api/pipeline.py:  hits ─> should_refuse? ─yes─> refuse(chunks)       -> Refusal
                                          └─no──> generate(q, chunks)   -> Answer
                          │
   api/main.py  POST /ask  (PIPELINE=real)        GET /evidence/{id}  crops page PNG
```

**The seams you code against:**

- **`retrieval/base.py`**: `Retriever.search(query, k, product_family) -> list[Hit]`. Every
  retriever implements this and nothing else. The harness, the refusal gate and `/ask` never
  import a concrete class.
- **`retrieval/registry.py`**: name → class. A new retriever is one module plus one line
  here, and then `eval.run --retriever <name>` just works.
- **`core/config.py`**: every env key, for every package. Don't read `os.environ` anywhere else.
- **`core/chunks.py`**: the only reader of `chunks.jsonl` (`chunk_store()` is cached per process).
- **`api/models.py`**: the API contract. **Frozen.** Change what produces it, never its shape.
- **`generation/llm.py`**: the only place Claude is called. It returns a validated Pydantic
  object, or raises `GenerationTimeout`/`GenerationError`, which `/ask` maps to 504/502.

`PIPELINE=fixture` (the default) keeps `/ask` on the AS0.5 fixtures, so the deployed app keeps
working while the pieces land. Flip it to `real` once AS4.1 and AS4.2 pass their tests.

## Open tasks: where each one goes

Every stub raises `NotImplementedError("ASx.y: …")`. Its tests skip with that message until
you fill it in, and then they run with no further edits. Tests already written for you are
listed below. The docstrings in each file carry the details.

| Task | File(s) to fill | Tests that turn on | Done-check |
|---|---|---|---|
| ~~AS2.2~~ done | `retrieval/baseline.py` | `test_retrieval::test_baseline_meets_contract` | baseline 0.36 overall |
| **AS2.3** index | qdrant + bm25 done; **`build_fault_codes` (Postgres) left** | `tests/test_bm25.py` | `python -m retrieval.index` prints 3× `ok` |
| ~~AS3.1~~ done | `fusion.py`, `bm25.py`, `codes.py` (fault-code lane), `scope.py` (family from question) | `test_fusion`, `test_bm25`, `test_codes`, `test_scope` | fused 0.56 vs baseline 0.36; see PRESENTER_NOTES.md |
| **AS3.2** threshold | none. Run `eval.calibrate`, set `REFUSAL_THRESHOLD` | `test_retrieval::test_confidence_gate` (passes) | calibrate exits 0 |
| **AS4.1** generation | `generation/generate.py::finalize`, tune `generation/prompt.py::SYSTEM` | `test_generation` (4 finalize tests + pipeline) | `eval.run --retriever fused --answers` |
| **AS4.2** refusal | `generation/refusal.py::refuse` | `test_generation::test_refusal_*`, `test_pipeline_refuses_*` | |
| **AS4.3** wire | set `PIPELINE=real` on the host, drop the stub knobs from `CONTRACT.md` | `tests/test_api.py` against real mode | deployed URL answers G01 with real cites |
| AS1.3 figures | `ingest/` (no figure chunks exist yet) | | diagram recall moves off the keyword floor |
| AS1.4 OCR | `ingest/` (`acs550_to_acs580_replacement` has **0 chunks**) | | `scanned` row > 0.00 |

The critical path runs AS2.3 → AS3.1 → AS4.1 → AS4.3. AS2.2, AS4.2 and AS1.4 hang off it and
can be done in parallel by whoever isn't on it.

**Current numbers** (`keyword` stand-in, token overlap, no services): recall@5 **0.44** overall,
0.83 fault_code, **0.00 scanned**. This is a floor, not the baseline: AS2.2 is the comparison
column. If the fused retriever can't beat 0.44, something is wrong.

## Conventions

- **Branch per task, commit prefix = task id**: `as3.1-rrf`, `AS3.1: rrf fusion with k=60`.
- **Pages are 1-based PDF indexes**, never the printed number (see `tools/CONTEXT.md`).
- **`bbox` is PDF points, origin bottom-left.** `schema.md` is the contract, `ingest/schema.py` the check.
- **Eval runs are committed**: `eval/results/<retriever>.json`. A number in the deck that isn't
  in a committed file doesn't exist (AS7.2).
- **Before writing a helper script, read `tools/CONTEXT.md`.** It may already exist.
- `pytest` green before pushing. A skip that says `pending:` is fine. A failure is not.
