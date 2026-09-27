# Upload your own manual + "Open in the manual" links: design

Date: 2026-09-27 · Status: approved in chat, pending spec review

## Why

- **Upload (live demo moment):** a judge uploads a short manual AskManual has never seen and gets a
  cited answer within a couple of minutes. That shows the pipeline generalises beyond the 7
  pre-indexed manuals. It is not a multi-user document store.
- **Source links:** every cited page links to the manufacturer's own online document at that page,
  so a technician can go from our crop to the full manual in one tap.

## Part 1: "Open in the manual" links

**Data.** `api/site.py` `MANUALS` gains a `url` per document: the ABB library link, each one
checked on 2026-09-27 to return `application/pdf`:

    https://search.abb.com/library/Download.aspx?DocumentID=<ID>&LanguageCode=en&DocumentPartId=<P>&Action=Launch

| doc_id | ID | P |
|---|---|---|
| acs880_primary_firmware_manual | 3AUA0000085967 | 1 |
| acs580_firmware_manual | 3AXD50000016097 | 1 |
| acs580_01_hardware_manual | 3AXD50000044794 | 1 |
| acs880_01_hardware_manual | 3AUA0000078093 | 1 |
| fpno21_profinet_adapter_manual | 3AXD50000158614 | 1 |
| acs580_technical_catalog | ACS580-PHTC01U-EN | (empty) |
| acs550_to_acs580_replacement | 3AXD50000660681 | (empty) |
| acs580_01_type4x_quickstart | 3AXD50001020156 | (empty) |

**Link target.** `<url>#page=<page>`. Desktop PDF viewers honour the fragment; mobile browsers often
download instead, so the link text always states the page: "Open p. 553 in ACS580 firmware manual ↗".
Links open in a new tab with `rel="noopener"`.

**Where they appear.**
1. Under every opened evidence crop, beside its caption.
2. In the answer's Sources list: each document title links to its first cited page.
3. On the refusal card, for each nearest passage.
4. On the Manuals page: each title links to the document.

**Delivery.** The answer page already receives `window.DOC_TITLES`; it additionally receives
`window.DOC_URLS` (doc_id → url). For an upload, the page receives that upload's own file URL
(`/uploads/<id>/file.pdf`). A doc with no URL renders no link rather than a broken one.

## Part 2: Upload (option A: private workspace per upload)

### User flow
1. New nav tab **Upload** (`/upload`): file picker, with the limits stated above the button.
2. Submit → `POST /uploads` → 202 `{id}` → the page polls `GET /uploads/{id}` every second and shows
   *Queued (position n) → Reading pages (i/N) → Indexing → Ready*, or the failure reason.
3. Ready → navigate to `/?doc=<id>`. The Ask page shows "Asking: **file.pdf** · change" and submits
   to `/answer?q=…&doc=<id>`, which calls `POST /uploads/{id}/ask`.
4. Answers, crops, "not found" and source links behave exactly as for the library.

### Limits (checked in this order, cheapest first)
| Check | Rejection message | HTTP |
|---|---|---|
| content type / `%PDF-` magic | "That isn't a PDF." | 415 |
| size ≤ 20 MB | "PDF is larger than 20 MB." | 413 |
| opens, not encrypted | "This PDF is password-protected." | 422 |
| pages ≤ 30 | "PDF has N pages; the limit is 30." | 422 |
| text layer on ≥ half the pages | "This PDF is a scan with no text layer; OCR isn't supported yet." | 422 (at the job's `failed` state) |
| ≤ 20 live uploads | "Too many uploads right now; try again later." | 503 |

The first four run synchronously in `POST /uploads`. The text-layer check runs first in the job.

### Components
- **`uploads/` package** (new top-level, next to `ingest/` and `retrieval/`):
  - `store.py`: `Upload` dataclass (id, filename, state, progress, error, created, chunks, index)
    and the in-memory registry with TTL expiry (2 h), swept on each access. Files live under
    `config.UPLOADS_DIR/<id>/` (`file.pdf`, `pages/*.png`) and are deleted on expiry.
  - `job.py`: `run(upload)`: open with PyMuPDF → text-layer check → `ingest.parse.parse_document`
    (doc_id `upload_<id>`, families `["UPLOAD"]`) → render each page at 150 dpi → build the index.
    One `ThreadPoolExecutor(max_workers=1)`: jobs are serial, and queue position is reported.
- **`retrieval/memory.py`**: `MemoryIndex(chunks)` builds three retrievers over one chunk list:
  BM25 (the same `index_text` and `tokens` as the library), dense (numpy matrix from
  `retrieval.embed`, cosine), and `CodeRetriever(chunks)`, fused with `FusedRetriever(..., scope=False)`.
  All exact reuse, no new ranking logic.
- **`api/pipeline.py`**: `answer_question` gains an optional `store` (chunk_id → Chunk), defaulting
  to `chunk_store()`, so upload chunks resolve without touching the library store.
- **`api/main.py`**: routes `GET /upload`, `POST /uploads`, `GET /uploads/{id}`,
  `POST /uploads/{id}/ask` (body `AskRequest`, response `AskResponse`, unchanged models),
  `GET /uploads/{id}/file.pdf`. `/evidence/{chunk_id}` falls back to the upload registry for
  `upload_…` ids and crops from that upload's pages dir.
- **`core/config.py`**: `UPLOADS_DIR` (default `uploads_data/`, git-ignored), plus the limits as
  constants in `uploads/store.py`.

**Unchanged:** `api/models.py`, the `/ask` contract, the library indexes and the eval. Uploads never
enter `chunks.jsonl`, Qdrant, BM25 or `eval/results`.

### Errors
- A job exception moves the upload to `failed` with a user-facing message. The traceback is logged
  server-side and never sent to the client.
- Unknown or expired id → 404 "This upload has expired or doesn't exist." The Ask page then drops
  back to the library.
- Generation errors map to 502/504, exactly as `/ask` does.

### Security and honesty (stated on the Upload page and in the README)
- Ids are 16 random hex characters (`secrets.token_hex(8)`). There are no accounts: the link is the
  access control. Nothing lists uploads.
- The filename is display-only and never used as a path.
- PDFs are parsed in the server process: acceptable for a demo, not for production.
- State is in memory: a restart clears it, and the app must run as a single process.
- Uploads are not measured (no gold questions).

## Testing
- `tests/test_memory_index.py`: MemoryIndex over the fixture chunks finds the 2330 row via BM25 and
  the code lane; the fused order is deterministic.
- `tests/test_uploads.py`: builds a 3-page text PDF with PyMuPDF in-test and runs it through the
  lifecycle (queued → ready, with the embedder stubbed for speed). Also: each rejection row in the
  limits table, and the text-layer failure using a PDF with an image-only page. `/evidence` serves an
  upload chunk. `POST /uploads/{id}/ask` returns an Answer with `llm.structured` monkeypatched.
  Expiry deletes files. An unknown id returns 404.
- `tests/test_api.py`: the answer page carries `DOC_URLS`; every catalogued manual has a URL.
- Manual: upload a real 15-page manual in the browser (the quickstart PDF) and ask a question
  with the real model.

## Out of scope
OCR for scanned uploads; accounts or sharing; persisting uploads across restarts; mixing an upload
with the library in one search; measuring upload quality.
