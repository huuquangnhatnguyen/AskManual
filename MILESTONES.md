# AskManual — Milestones

Prototype phase for AskManual: photograph or describe a fault on an industrial drive and get a structured, cited answer drawn from the manufacturer's own manuals, with every claim expanding to the cropped page region it came from.
**Stack:** Python · FastAPI · Qdrant · BM25 · Postgres · vision LLM · server-rendered phone-width web UI
**Delivery:** a public HTTPS URL a judge can open on a phone, plus a repo that comes up locally with `docker compose up`.

**Sequencing principle:** two orderings, and they do not conflict.

*Delivery before pipeline.* A deployed, phone-reachable app shell exists before any pipeline code. Reachability — hosting, HTTPS, camera capture on a real handset — is the riskiest unknown in the project, and it is the one thing that cannot be recovered from if it is discovered late. Found on D5 it costs an afternoon; found on D9 it costs the submission. The skeleton goes up serving fixtures, behind an API contract that does not change when the real pipeline lands behind it.

*Measurement before retrieval.* The eval harness and gold question set come before any retriever, so every later decision is measured against a known baseline rather than guessed at. Writing the ingest pipeline before the gold set means discovering retrieval failures with no time left to fix them.

**Estimate:** 64.75h across 33 tasks — against roughly 5 days remaining. This does not fit; see **Re-cut against the remaining window** below.

**Window:** Sep 18, 2026 16:00 UTC → Sep 27, 2026 21:59 UTC (5:59 PM Eastern) · solo
**Deliverables due at the end:** working prototype · demo video · source code · technical documentation · presentation deck

Status legend: `TODO` · `DOING` · `DONE` · `BLOCKED`

**How to read a task.** Each milestone opens with an index table — id, task, estimate, dependencies, status — and every row has a detail block below it in the same order. A detail block is three lists and nothing else:

- **Input** — what must already exist before you start. If an input is missing, the task is `BLOCKED`, not `DOING`.
- **Output** — the artifacts the task leaves behind. Named files and commands, not activities. If it is not a file or a running thing, it is not output.
- **Done when** — the checks that decide `DONE`. Written so someone else could run them without asking you a question.

---

## Day map

Re-cut on Sep 22 after the original map slipped: the first four days produced the M0 artifacts but no code, and the plan had no task that produced a runnable application at all.

| Day | Date | Milestone | Exit condition |
|---|---|---|---|
| D1–D4 | Sep 18–21 | M0 artifacts | Corpus, schema, gold set written |
| D5 | Mon Sep 22 (PM) | M0 skeleton | **A public URL answers a stubbed question from a phone** |
| D6 | Tue Sep 23 | M1 Ingestion | Chunks on disk with bbox |
| D7 | Wed Sep 24 | M2 Index + baseline + eval | **First recall@5 numbers** |
| D8 | Thu Sep 25 | M3 + M4 | Fused retrieval beats baseline; real cited answers live behind `/ask` |
| D9 | Fri Sep 26 | M6 + M7 | Evidence pane works on the live URL; freeze; final numbers |
| D10 | Sat Sep 27 | M8 | Video, README, deck — submitted by 17:00 ET |

M5 does not appear on this map. See **Re-cut against the remaining window**.

---

## M0 — Foundations and walking skeleton (11.5h)

Two halves, and no retrieval code in either.

The first three tasks produce artifacts — the corpus, the chunk schema, the gold question set — that determine everything downstream and are expensive to change once code depends on them. The schema in particular cannot be retrofitted: bbox coordinates are discarded at parse time, so recovering them later means re-ingesting the whole corpus. Five manuals is a deliberate ceiling, because every additional manual is a fresh set of parse failures to debug and needs its own gold questions, or it contributes nothing measurable.

The last five produce a **walking skeleton**: a scaffolded repo, a FastAPI service whose four routes return schema-valid fixtures, a phone-width interface that renders them, and all of it deployed to a public HTTPS URL and opened on an actual phone. None of it depends on the pipeline. The point is that the API contract fixed in AS0.5 is the seam — M1 through M4 fill in what sits behind it without the interface changing, and the answer to "does it run and can a judge reach it" is known on D5 instead of D9.

The schema a retrievable unit carries:

```json
{
  "chunk_id": "acs580_p214_t03_r07",
  "doc_id": "acs580_firmware_manual",
  "product_family": "ACS580",
  "page": 214,
  "bbox": [72.4, 318.0, 523.1, 341.6],
  "chunk_type": "table_row",
  "text": "F0001 | Overcurrent | Motor cable short circuit; excessive load | Check motor cable insulation; reduce load",
  "parent_section_id": "6.3",
  "parent_section_title": "Fault tracing",
  "fault_codes": ["F0001"],
  "source_image": "pages/acs580_p214.png"
}
```

`bbox` is in PDF points, origin bottom-left, `[x0, y0, x1, y1]` — the same coordinate space the parser reports, so the crop is a direct transform.

| ID | Task | Est | Depends | Status |
|----|------|-----|---------|--------|
| AS0.1 | Fix the corpus | 1h | — | DOING |
| AS0.2 | Write the chunk schema | 1h | — | DOING |
| AS0.3 | Write the 25 gold questions | 2.5h | — | DOING |
| AS0.4 | Scaffold the repo and services | 1.5h | AS0.2 | DOING |
| AS0.5 | API contract with stubbed endpoints | 1.5h | AS0.4 | TODO |
| AS0.6 | Phone-width UI shell against the stubs | 2h | AS0.5 | TODO |
| AS0.7 | Deploy to a public HTTPS URL | 1.5h | AS0.5 | TODO |
| AS0.8 | Phone check on the live URL | 0.5h | AS0.6, AS0.7 | TODO |

#### AS0.1 — Fix the corpus

**Input**
- ABB's public document library (`library.abb.com`)
- `pdftotext` on PATH, for the no-text-layer check

**Output**
- `corpus/` — 5 PDFs, at least one genuinely scanned with no text layer
- `corpus.md` — one row per file: filename, product family, page count, and whether it is scanned

**Done when**
- `pdftotext file.pdf -` prints nothing for at least one file in the corpus
- Every file in `corpus/` has a row in `corpus.md`, and every row points at a file that exists

#### AS0.2 — Write the chunk schema

**Input**
- A handful of representative pages from the corpus: one fault-code table, one wiring figure, one prose section
- The coordinate space the parser reports, confirmed against one real page

**Output**
- `schema.md` — the full field list a retrievable unit carries: `chunk_id`, `doc_id`, `product_family`, `page`, `bbox`, `chunk_type`, `text`, `parent_section_id`, `parent_section_title`, `fault_codes`, `source_image`
- One sentence per field stating what breaks downstream if it is missing

**Done when**
- Every field in the JSON example in MILESTONES.md M0 has an entry in `schema.md`
- `bbox` is specified as PDF points, origin bottom-left, `[x0, y0, x1, y1]`
- Someone holding only `schema.md` can render a chunk's crop from `page` + `bbox` without asking a question

#### AS0.3 — Write the 25 gold questions

**Input**
- The corpus PDFs, opened by hand — a cited page is not trusted until it has been looked at
- `tools/pdfgrep.py` and `tools/pdfpage.py` for locating and reading candidate pages

**Output**
- `eval/gold.jsonl` — 25 entries, each carrying `question`, `query_type`, `answer_gist`, `doc_id` and `page` (1-based PDF page index, not the number printed on the page)

**Done when**
- Roughly 6 questions per query type
- At least one `cross_manual` question
- At least three questions whose answers exist only in the scanned manual
- Every cited page verified against the PDF — `python tools/verify_gold.py` exits 0

#### AS0.4 — Scaffold the repo and services

**Input**
- `schema.md` — the chunk contract the package layout is built around
- Docker available locally

**Output**
- A git repository, initialised, with `.gitignore` covering `corpus/`, `pages/`, `chunks.jsonl` and `.env`
- `pyproject.toml` with pinned dependencies
- Package skeleton: `ingest/`, `retrieval/`, `generation/`, `api/`, each importable
- `eval/` restructured so `python -m eval.run` resolves — the gold data moves to `eval/data/`, since a data directory and a module cannot share a name
- `docker-compose.yml` bringing up Qdrant and Postgres
- `.env.example` naming every key the app reads, with no values in it

**Done when**
- `docker compose up -d` leaves Qdrant and Postgres both answering
- `python -c "import ingest, retrieval, generation, api"` exits 0
- `git status` is clean, and no corpus PDF, page render or key is tracked

#### AS0.5 — API contract with stubbed endpoints

**Input**
- The answer schema in MILESTONES.md M4 — the response shape is fixed now, before anything produces it
- The scaffold from AS0.4

**Output**
- A FastAPI app exposing four routes:
  - `POST /ask` — `{question, product_family?}` → an answer object in the M4 shape
  - `POST /identify` — image upload → `{model_number?, fault_code?}`
  - `GET /evidence/{chunk_id}` — a cropped page PNG
  - `GET /health` — reports whether Qdrant and Postgres are reachable
- Every route returning hardcoded, schema-valid fixture data
- Command: `uvicorn api.main:app`

**Done when**
- `/ask` returns a response that validates against the M4 answer schema, from a fixture
- `/evidence/{chunk_id}` returns a real PNG, cropped from one corpus page committed as a fixture
- The contract is written down, so AS4.3 fills these routes without the interface changing

#### AS0.6 — Phone-width UI shell against the stubs

**Input**
- The stubbed routes from AS0.5

**Output**
- A server-rendered interface at roughly 390px width, served by the same FastAPI app — no separate build step and no CORS, chosen because the schedule cannot absorb a second deployable
- Two entry paths on one screen: a typed question, and a photo input using `capture="environment"`
- A loading state and an error state

**Done when**
- Asking a question renders the fixture answer, with no console errors
- The loading state is visible — a three-second request does not show a blank screen
- Tapping the photo input on a phone opens the camera, not a file browser

#### AS0.7 — Deploy to a public HTTPS URL

**Input**
- The app from AS0.5 and its `docker-compose.yml`
- A host. Railway is the default, because the app, Postgres and a Qdrant container live in one project with no infrastructure work. Render and Fly.io are equivalent; Qdrant Cloud's free tier is the fallback if a managed vector store is easier than a container.

**Output**
- A public HTTPS URL serving the stubbed app
- Managed Postgres and a reachable Qdrant, with connection strings supplied as environment variables and not committed
- A redeploy path that is one step — push to main, or one command

**Done when**
- The URL opens from a logged-out browser on a network that is not yours
- `GET /health` reports both Postgres and Qdrant reachable *from the deployed app*, not from your laptop
- Redeploy is one step, because it will happen a dozen more times this week

#### AS0.8 — Phone check on the live URL

**Input**
- The deployed URL from AS0.7
- An actual phone, on cellular rather than your home wifi

**Output**
- A confirmed round trip: photo captured and uploaded from the phone, question asked, fixture answer rendered
- Every layout or capture problem found here, written down as a fix rather than left for D9

**Done when**
- The camera opens and an upload completes over the live HTTPS URL
- Done on a phone, not in devtools — the failure this task exists to catch does not reproduce in devtools

---

## M1 — Ingestion (12h)

Turns the corpus into schema-conforming chunks on disk. Everything here writes to `chunks.jsonl`; nothing is retrievable yet. Heading detection from PDF bookmarks is unreliable, so fall back to font-size and position heuristics. Output is two-level: small chunks for retrieval, with the parent section retained for generation context.

| ID | Task | Est | Depends | Status |
|----|------|-----|---------|--------|
| AS1.1 | Layout-aware parse to chunks | 4h | AS0.2, AS0.4 | TODO |
| AS1.2 | Table extraction as rows | 3h | AS0.2 | TODO |
| AS1.3 | Figure crops plus vision descriptions | 3h | AS0.2 | TODO |
| AS1.4 | OCR the scanned manual | 2h | AS0.1, AS0.2 | TODO |

#### AS1.1 — Layout-aware parse to chunks

**Input**
- `corpus/*.pdf`
- `schema.md` — the field contract every written chunk must satisfy

**Output**
- `chunks.jsonl` — one schema-conforming JSON object per line
- `pages/<doc>_p<n>.png` — the page renders that `source_image` points at
- Command: `python -m ingest.run corpus/`

**Done when**
- Ten randomly spot-checked chunks each carry a valid `page` and `bbox`
- For each of those ten, the text sitting at those coordinates in the PDF matches the chunk's `text`

#### AS1.2 — Table extraction as rows

**Input**
- The fault-code tables in the firmware manuals
- The `chunks.jsonl` writer from AS1.1

**Output**
- One chunk per table row, `chunk_type` = `table_row`, with `fault_codes` populated from the row's code column

**Done when**
- Grepping `chunks.jsonl` for `F0001` returns a single row-level chunk, not a page of text
- A flattened multi-row blob fails this check, however complete its text is

#### AS1.3 — Figure crops plus vision descriptions

**Input**
- Figure regions detected during the AS1.1 parse
- A vision model, called once per figure

**Output**
- One cropped PNG per detected figure
- One `chunk_type` = `figure` chunk per figure, whose `text` is the model's description

**Done when**
- Descriptions name what is visibly labelled — terminal names, part numbers, connector designations
- A description reading "a wiring diagram" fails this, since it is useless for retrieval

#### AS1.4 — OCR the scanned manual

**Input**
- The scanned, no-text-layer PDF identified in AS0.1
- An OCR engine that reports word-level coordinates

**Output**
- Text chunks for that document, carrying `bbox` like every other chunk, appended to `chunks.jsonl`

**Done when**
- At least one gold question targeting that manual has its answer text present in `chunks.jsonl`

---

## M2 — Index, baseline and eval harness (7h)

The critical milestone, and the one the whole plan is sequenced around. The harness is the instrument every later decision reads, so it is built before the retrievers, not after them. The naive baseline is built deliberately rather than as a strawman, because it is the comparison column in the final results table and an unfairly bad baseline makes the final numbers worthless.

**Exit gate — end of D3:** a two-column recall@5 table exists. If it does not, stop building features and finish this before anything else.

Expected shape of the harness output:

```
$ python -m eval.run --retriever baseline
type            n    recall@5
prose           6    0.83
table           7    0.29
diagram         6    0.17
fault_code      6    0.33
cross_manual    -    n/a
OVERALL        25    0.40
```

| ID | Task | Est | Depends | Status |
|----|------|-----|---------|--------|
| AS2.1 | Eval harness | 2h | AS0.3, AS0.4 | TODO |
| AS2.2 | Naive baseline retriever | 2h | AS2.1 | TODO |
| AS2.3 | Index the real chunks | 3h | AS1.1, AS2.1 | TODO |

#### AS2.1 — Eval harness

**Input**
- `eval/gold.jsonl`
- Any retriever registered under a name

**Output**
- A per-query-type table of `recall@5` and citation accuracy, plus an `OVERALL` row
- Command: `python -m eval.run --retriever <name>`

**Metric definitions — fixed here, not renegotiated later**
- `recall@5` — the fraction of gold questions whose known source page appears among the top 5 retrieved chunks
- citation accuracy — the fraction of produced answers whose cited page actually contains the answer

**Done when**
- Swapping retrievers is a flag, not an edit: a new retriever runs through the harness without changing harness code

#### AS2.2 — Naive baseline retriever

**Input**
- Raw text from `corpus/*.pdf` — no layout, no metadata
- The same embedding model the real pipeline uses

**Output**
- A retriever named `baseline`: 500-character blind chunking, dense embeddings only, no metadata filtering
- Its numbers, which become the comparison column of the final results table

**Done when**
- It reports both metrics through the AS2.1 harness, unmodified
- It is a fair baseline rather than a strawman — an unfairly bad one makes the final table worthless

#### AS2.3 — Index the real chunks

**Input**
- `chunks.jsonl` from M1 — all three indexes are built from this one file, so they cannot drift apart

**Output**
- A Qdrant collection carrying chunk payloads: `doc`, `page`, `bbox`, `type`
- A BM25 index over the same chunks
- A Postgres table of extracted fault-code rows

**Done when**
- `SELECT * FROM fault_codes WHERE code = 'F0001'` returns exactly one row
- All three indexes report the same chunk count as `chunks.jsonl`

---

## M3 — Hybrid retrieval (5h)

The first measured improvement over the baseline. Fusion is reciprocal rank fusion with k=60, chosen over weighted score fusion because it consumes ranks rather than scores, so BM25 and cosine values never need normalising against each other — be able to say that sentence in the demo.

```
score(d) = Σ  1 / (k + rank_i(d))        k = 60
        over each retriever i that returned d
```

| ID | Task | Est | Depends | Status |
|----|------|-----|---------|--------|
| AS3.1 | BM25 plus dense with RRF fusion | 4h | AS2.3 | TODO |
| AS3.2 | Confidence threshold for refusal | 1h | AS3.1 | TODO |

#### AS3.1 — BM25 plus dense with RRF fusion

**Input**
- The Qdrant collection and BM25 index from AS2.3
- The baseline numbers from AS2.2, as the thing to beat

**Output**
- A fused retriever runnable through the harness by name
- A recorded delta against the baseline, per query type

**Done when**
- Fusion is reciprocal rank with k=60 — ranks in, no score normalisation
- The fused retriever beats the baseline on `table` and `fault_code` queries
- The delta is written down, not remembered

#### AS3.2 — Confidence threshold for refusal

**Input**
- The fused top score from AS3.1
- `eval/out_of_corpus.jsonl` — 5 deliberately out-of-corpus questions, such as resetting a Siemens S7 PLC

**Output**
- A single tunable threshold on the fused top score
- The calibration run's output, showing where each question landed relative to it

**Done when**
- All 5 out-of-corpus questions refuse
- No gold question refuses

---

## M4 — Structured generation (7h)

Retrieved chunks become an answer with a fixed shape, where every field is traceable to a chunk and nothing is invented to fill a gap. The safety warning is the field that matters most: it is copied from source text, never rewritten, and that is asserted by test rather than trusted.

```json
{
  "fault_meaning": {"text": "...", "cite": "acs580_p214_t03_r07"},
  "probable_causes": [{"text": "...", "likelihood": "high", "cite": "..."}],
  "corrective_steps": [{"n": 1, "text": "...", "cite": "..."}],
  "tools_and_parts": [{"text": "...", "cite": "..."}],
  "safety_warning": {"verbatim": "WARNING! ...", "cite": "acs580_p31_p02"}
}
```

| ID | Task | Est | Depends | Status |
|----|------|-----|---------|--------|
| AS4.1 | Answer schema plus constrained generation | 4h | AS3.1 | TODO |
| AS4.2 | Refusal response | 1h | AS3.2 | TODO |
| AS4.3 | Wire real answers into the API | 2h | AS4.1, AS4.2, AS0.5 | TODO |

#### AS4.1 — Answer schema plus constrained generation

**Input**
- The top-k fused chunks from AS3.1, each with its parent section for context
- The answer schema in MILESTONES.md M4

**Output**
- A JSON answer carrying `fault_meaning`, `probable_causes`, `corrective_steps`, `tools_and_parts` and `safety_warning`
- A `cite` chunk id on every field, resolvable back to a chunk in `chunks.jsonl`

**Done when**
- Any field unsupported by a retrieved chunk comes back empty rather than invented
- A test asserts `safety_warning.verbatim` appears character-for-character in the cited chunk

#### AS4.2 — Refusal response

**Input**
- A fused top score below the AS3.2 threshold

**Output**
- A refusal message, plus the top 3 chunks the system did find, with their page numbers

**Done when**
- The refusal payload contains no corrective steps of any kind — not hedged ones, not "you might try" ones

#### AS4.3 — Wire real answers into the API

**Input**
- The generator from AS4.1 and the refusal path from AS4.2
- The stubbed routes from AS0.5, whose contract does not change — this task replaces what is behind them, nothing in front

**Output**
- `POST /ask` calling the real pipeline: retrieve, fuse, generate, or refuse
- `GET /evidence/{chunk_id}` resolving a real chunk id to `page` + `bbox` and returning that region cropped from `pages/*.png`
- A timeout and an error response for a generation call that hangs or fails

**Done when**
- The deployed URL answers a real gold question with real citations, and no fixture remains anywhere in that path
- An out-of-corpus question refuses through the API, not only in a test
- An unknown or malformed `chunk_id` returns 404, not a stack trace

---

## M5 — Nameplate photo entry (5h)

The feature that makes this feel like a field tool rather than a search box: photograph the nameplate or the keypad showing a fault code, and retrieval scopes itself to the right product family before the query runs.

**Cut as of the Sep 22 re-cut.** The measured results table is worth more to the submission than this is, and 5h does not exist. Cutting it leaves `POST /identify` stubbed and the photo entry path hidden in the interface; the typed-question path is untouched. Restore this milestone only if M1–M4 land a full day early.

| ID | Task | Est | Depends | Status |
|----|------|-----|---------|--------|
| AS5.1 | Nameplate and keypad photo extraction | 2h | — | TODO |
| AS5.2 | Scope retrieval by extracted product family | 2h | AS5.1, AS3.1 | TODO |
| AS5.3 | Manual override for failed extraction | 1h | AS5.1 | TODO |

#### AS5.1 — Nameplate and keypad photo extraction

**Input**
- A photo of a drive nameplate, or of a keypad showing a fault code
- 5 test images — web images are acceptable for the demo
- A vision model

**Output**
- Structured fields: model number and/or fault code
- A recorded extraction accuracy across the 5 images

**Done when**
- The accuracy figure comes from an actual run and is written down, not estimated

#### AS5.2 — Scope retrieval by extracted product family

**Input**
- The model number extracted in AS5.1
- The fused retriever from AS3.1

**Output**
- Retrieval filtered to the matching `product_family` before the query runs

**Done when**
- Demonstrated end to end: photo upload → scoped retrieval → cited answer

#### AS5.3 — Manual override for failed extraction

**Input**
- An extraction that failed or returned the wrong model

**Output**
- A typed-entry path for model number or fault code, feeding the same scoping as AS5.2

**Done when**
- A typed value scopes retrieval identically to an extracted one
- The failure path is demonstrable on camera — showing it is a strength, not a gap

---

## M6 — Interface and evidence pane (6h)

This is the demo. The shell itself was built and deployed back in AS0.6, at roughly 390px width from the first commit rather than a desktop layout shrunk at the end, because the whole premise is a technician holding a phone in front of a drive. What happens here is the part that could not be done against fixtures: real answers are slow, sometimes refuse, and sometimes fail.

The evidence pane is the headline feature, so it is also the headline risk: a crop that renders the wrong page region is worse than no crop at all.

| ID | Task | Est | Depends | Status |
|----|------|-----|---------|--------|
| AS6.1 | Harden the shell for real answers | 2h | AS0.6, AS4.3 | TODO |
| AS6.2 | Structured answer card | 2h | AS4.3 | TODO |
| AS6.3 | Citation expands to cropped page image | 2h | AS6.2, AS0.3, AS4.3 | TODO |

#### AS6.1 — Harden the shell for real answers

**Input**
- The deployed shell from AS0.6, which has been serving fixtures since D5
- Real answers from AS4.3, which are slower than fixtures and sometimes refuse

**Output**
- A loading state sized for a real generation call rather than a fixture's instant return
- The refusal response rendered as its own state, visually distinct from an answer
- An error state for a timeout or a failed upload

**Done when**
- A real answer, a refusal and a timeout each produce a distinct screen
- Checked on a phone against the live URL, not locally

#### AS6.2 — Structured answer card

**Input**
- The answer JSON served by `POST /ask` (AS4.3)

**Output**
- A card rendering each schema field as its own labelled section

**Done when**
- The safety warning is visually distinct from everything else on screen — findable without reading

#### AS6.3 — Citation expands to cropped page image

**Input**
- Each field's `cite` chunk id, resolved to `page` + `bbox`
- The page renders in `pages/*.png` from AS1.1

**Output**
- An expandable evidence pane showing the page image cropped to that chunk's bbox

**Done when**
- Verified against all 25 gold questions rather than a sample of 3 — a crop rendering the wrong region turns the headline feature into the headline failure

---

## M7 — Freeze and final evaluation (2.25h)

The point where building stops and measuring starts. After the freeze the only permitted work is bug fixes and improvement to the single worst-performing query type; the results table produced here is what goes in both the deck and the README.

| ID | Task | Est | Depends | Status |
|----|------|-----|---------|--------|
| AS7.1 | Feature freeze | 0.25h | AS6.3 | TODO |
| AS7.2 | Final eval run and results table | 2h | AS2.2, AS3.1, AS7.1 | TODO |

#### AS7.1 — Feature freeze

**Input**
- AS6.3 complete — the evidence pane works end to end

**Output**
- A commit tagged for freeze

**Done when**
- After the tag, the only commits are bug fixes and work on the worst-performing query type. No new features.

#### AS7.2 — Final eval run and results table

**Input**
- The baseline retriever (AS2.2) and the fused retriever (AS3.1), both run after the freeze commit

**Output**
- The results table for the deck and README: baseline versus pipeline, `recall@5` and citation accuracy, broken out by query type
- The raw harness output, committed alongside the table

**Done when**
- Every number in the table traces to a committed harness run — no figure exists only in the deck

---

## M8 — Submission package (9h)

Nothing new is built here; the work is making what exists legible to a judge who has never seen it. The video carries the most weight per hour spent, so it is sequenced first.

| ID | Task | Est | Depends | Status |
|----|------|-----|---------|--------|
| AS8.1 | Demo video | 3h | AS6.3, AS4.2, AS7.2 | TODO |
| AS8.2 | README and technical documentation | 3h | AS7.2, AS8.5 | TODO |
| AS8.3 | Update the deck with real numbers | 1h | AS7.2 | TODO |
| AS8.4 | Submit | 1h | AS8.1, AS8.2, AS8.3 | TODO |
| AS8.5 | Reproducible run for a judge | 1h | AS7.1 | TODO |

#### AS8.1 — Demo video

**Input**
- The working prototype, frozen
- The results table from AS7.2

**Output**
- A video under 3 minutes, recorded on a phone, in this order:
  1. Photograph the fault
  2. The structured answer
  3. Expand a citation to show the cropped diagram
  4. Ask something out of corpus and let it refuse
  5. Show the numbers table

**Done when**
- There is no architecture narration anywhere in it

#### AS8.2 — README and technical documentation

**Input**
- The repo as frozen, `schema.md`, and the AS7.2 results table

**Output**
- Setup instructions a judge can actually run
- An architecture section, the chunk schema, the eval methodology, the results table, and known limitations stated plainly

**Done when**
- A clean clone reaches a running prototype by following the README alone

#### AS8.3 — Update the deck with real numbers

**Input**
- The final results table (AS7.2)
- The Idea Phase deck

**Output**
- The deck with every "to be reported" cell replaced by a measured value

**Done when**
- No placeholder cells remain anywhere in the deck

#### AS8.4 — Submit

**Input**
- Video link, public repo, updated deck, README

**Output**
- All submission fields filled

**Done when**
- The repo is public
- The video link opens from a logged-out browser
- Submitted by 17:00 ET on Sep 27, not 17:55

#### AS8.5 — Reproducible run for a judge

**Input**
- The frozen repo
- The ingest artifacts: `chunks.jsonl`, `pages/*.png`, and the populated Qdrant collection

**Output**
- A published index artifact — a Qdrant snapshot, or a seed script that loads a committed `chunks.jsonl` — so that nobody has to rerun a twelve-hour ingest with paid vision calls to see the thing work
- `docker compose up` bringing the whole application up locally against that artifact

**Done when**
- A clean clone reaches a working local prototype with no LLM key needed for ingest — a key is needed only to generate answers
- The run is timed, and that time is stated in the README

---

## Dependency spine

```
M0 artifacts ──> M1 ──> M2 ──> M3 ──> M4 ──┬──> M6 ──> M7 ──> M8
                                           │
M0 skeleton ───────────────────────────────┘
(AS0.4 → AS0.5 → AS0.6/AS0.7 → AS0.8)      └──> M5 (cut)
```

The skeleton branch runs to a deployed URL on D5 and then waits. M4's last task, AS4.3, is where the two branches meet: the pipeline moves in behind an API contract that has been live and exercised for four days by then.

Critical path: **AS0.2 → AS0.4 → AS1.1 → AS2.3 → AS3.1 → AS4.1 → AS4.3 → AS6.2 → AS6.3 → AS7.1 → AS7.2 → AS8.1 → AS8.4** — 29.75h of the 64.75h total.

M5 hangs off M3 and feeds only the demo video, which is why it can be cut without breaking anything downstream.

---

## Re-cut against the remaining window

Effort is 64.75h across 33 tasks. The window closes Sep 27 at 17:00 ET, which from the evening of Sep 22 is about five working days. That is roughly thirteen hours a day, solo, and it does not happen.

So the cut list below is no longer contingency. Applying its first three items:

1. **M5 entirely** (AS5.1, AS5.2, AS5.3) — saves 5h, leaving 59.75h
2. **AS1.3 reduced to wiring diagrams only**, no decorative figures — saves 1.5h, leaving 58.25h
3. **The fifth manual**, if AS1.1 overruns on parse failures — saves roughly 1.5h, leaving 56.75h

56.75h over five days is still eleven hours a day. If that is not the shape of the week, the next things to go are the demo video's production value and then AS8.3. Decide that now rather than at 02:00 on D9.

**Never cut:** AS2.1 (eval harness), AS3.1 (hybrid retrieval), AS6.3 (evidence pane), AS0.7 (it is reachable at all). The first three are the submission; the fourth is whether anyone can see it.

---

## Cut list — if you fall behind, drop in this order

1. Cross-manual gold questions (drop the claim from the deck too)
2. Figure descriptions for decorative figures; keep wiring diagrams only
3. **M5 entirely** (AS5.1, AS5.2, AS5.3) — painful, but the measured table is worth more
4. Fifth manual

**Never cut:** AS2.1 (eval harness), AS3.1 (hybrid retrieval), AS6.3 (evidence pane). Those three are the submission.
