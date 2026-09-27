# API contract

Fixed in AS0.5. AS4.3 replaces what sits *behind* these routes and nothing in
front of them: same paths, same request and response shapes. The Pydantic
models in `api/models.py` are the check; this file is the prose.

Run: `uvicorn api.main:app` · interactive schema at `/docs`.

## `POST /ask`

Request: `{"question": str (1–1000 chars), "product_family": str | null}`

Response: one of two shapes, told apart by `kind`.

**`kind: "answer"`** — the M4 answer, plus `sources`:

```json
{
  "kind": "answer",
  "fault_meaning": {"text": "...", "cite": "<chunk_id>"} | null,
  "probable_causes": [{"text": "...", "likelihood": "high|medium|low", "cite": "<chunk_id>"}],
  "corrective_steps": [{"n": 1, "text": "...", "cite": "<chunk_id>"}],
  "tools_and_parts": [{"text": "...", "cite": "<chunk_id>"}],
  "safety_warning": {"verbatim": "WARNING! ...", "cite": "<chunk_id>"} | null,
  "sources": {"<chunk_id>": {"doc_id": "...", "page": 553, "chunk_type": "table_row", "parent_section_title": "Fault messages"}}
}
```

- A field the retrieved chunks don't support is `null` or `[]`, never filled in.
- Every `cite` has an entry in `sources` (enforced by the model), so the UI can
  label a citation "p. 553" without another request.
- `safety_warning.verbatim` appears character-for-character in the cited chunk's `text`.

**`kind: "refusal"`** — fused top score below the AS3.2 threshold:

```json
{"kind": "refusal", "message": "...", "nearest": [{"chunk_id": "...", "doc_id": "...", "page": 553, "text": "..."}]}
```

At most 3 `nearest`. There is no steps field in this shape at all.

Errors: `422` for an invalid body. AS4.3 adds `504` for a generation timeout
and `502` for a failed generation call, both as `{"detail": str}`.

**Fixture-mode query params** (`PIPELINE=fixture`, the default; ignored when `PIPELINE=real`): `?fixture=refusal` returns the
refusal fixture; `?delay=<0–10>` sleeps first, to exercise the loading state.
The UI forwards both from its own URL, e.g. `/?delay=3`.

## `POST /identify`

Multipart, field `image` (any `image/*`, ≤ 15 MB) →
`{"model_number": str | null, "fault_code": str | null}`.
`415` if not an image, `413` if too large, `422` if empty.
Stays stubbed while M5 is cut.

## `GET /evidence/{chunk_id}`

`image/png` — the chunk's `bbox` cropped out of its 150 dpi page render,
padded 6 pt, per `schema.md`. `404` for an unknown or malformed id, never a
stack trace. Stub serves the chunks in `api/fixtures/chunks.jsonl`; AS4.3
points the same code at `chunks.jsonl` and `pages/`.

## `GET /health`

```json
{"status": "ok|degraded", "qdrant": {"ok": true, "detail": "HTTP 200"}, "postgres": {"ok": true, "detail": "SELECT 1"}}
```

Always `200`; read `status`. `detail` names the failure kind only — never a
connection string. Reads `QDRANT_URL`, `QDRANT_API_KEY`, `DATABASE_URL`.

## `GET /`

The phone-width UI shell (AS0.6), `api/templates/index.html`.
