# Presenter notes

One section per feature: what it does, why it's built that way, the number that proves it,
and what a judge might ask. Written to be understood, not just read aloud.

## AS3.1 — Hybrid retrieval (dense + BM25 + fault-code lane, fused with RRF)

**The problem.** A technician asks "ACS580 is showing fault 2330, what do I check?". The
answer is one row in a 600-page firmware manual. No single search method finds every kind
of question:

- **Dense (embeddings)** understands meaning ("motor won't start" ≈ "no rotation"), but a
  code like `2330` is just a number to it.
- **BM25 (keywords)** matches exact words, but it penalises long chunks. The 2330 row is
  ~200 tokens against a median chunk of 17, so BM25 alone put it at **rank 14**.
- **Fault-code lane** is an exact lookup: if the question contains a code that the manuals
  define (377 of them, tagged at ingest), return the rows that define it. Rows from the
  product family named in the question come first.

**How they combine: Reciprocal Rank Fusion (RRF).** Each method produces a ranked list.
Every chunk scores `1 / (60 + rank)` per list it appears in, and the scores are summed.
Only *ranks* matter, never raw scores, because BM25 scores (~20) and cosine scores (~0.8)
aren't comparable and normalising them is guesswork. A chunk that shows up high in two lists
beats one that tops just one. Code: `retrieval/fusion.py` (the `rrf` function is ~10 lines).

**Why three lanes and not two.** The plan said dense + BM25. The fault-code lane was the
planned Postgres `fault_codes` table. Here it reads `chunks.jsonl` directly, so it needs
no database and can't drift out of sync with the other indexes. RRF takes any number of lists.

**Scoping by product family.** If the question names exactly one drive family ("ACS580-01
frame R1"), retrieval searches only that family's manuals. An ACS580 question answered from
the ACS880 manual is wrong even when the words match. When two families are named ("swapping
an ACS550 for an ACS580"), it searches everything, because that's a cross-manual question.
This is a text-only stand-in for the nameplate-photo feature (M5), which was cut.
Code: `retrieval/scope.py`.

**Numbers (recall@5, 25 gold questions; files in `eval/results/`):**

| retriever | prose (6) | table (7) | diagram (6) | fault code (6) | overall (25) |
|---|---|---|---|---|---|
| baseline: raw PDF text, 500-char chunks, dense only | 0.50 | 0.29 | **0.50** | 0.17 | 0.36 |
| BM25 alone | 0.17 | **0.57** | 0.33 | 0.67 | 0.44 |
| dense alone | 0.33 | 0.29 | 0.33 | 0.50 | 0.36 |
| **fused (ours)** | **0.50** | 0.43 | 0.33 | **1.00** | **0.56** |

Headline: **fault-code questions go from 1 in 6 to 6 in 6**, and overall from 0.36 to 0.56.
Fault codes are the main use case: a technician standing at a drive showing a code.

**Say these out loud before a judge finds them:**
- **Diagrams are worse than the baseline (0.33 vs 0.50).** Figure ingestion (AS1.3) was cut,
  so our structured chunks carry no figure labels, while the baseline's raw page text does.
  With 6 questions, that's a single question's difference.
- **Tables:** fused beats the baseline, but BM25 on its own scores higher (0.57 vs 0.43).
  Dense retrieval pulls some table rows down.
- **2 of the 7 table questions and all 3 "scanned" questions are unanswerable for every
  retriever,** because the scanned ACS550→ACS580 manual has no OCR yet (AS1.4). Every
  column shares that ceiling equally.
- **n = 25.** One question moves a slice by 0.14–0.17. These are directional numbers, not
  statistically significant ones.

**Things we deliberately did *not* do.** Lowering BM25's length penalty (`b`) raised recall
from 0.44 to 0.56 on our gold set. We didn't ship it, because choosing it by looking at the
25 test questions is tuning on the test set. A judge who asks gets that answer.

**Likely questions**
- *Why k=60?* It's the constant from the original RRF paper (Cormack et al., 2009) and is
  robust across datasets. We didn't tune it.
- *What if a question has no fault code?* The code lane returns nothing and fusion runs on
  dense + BM25 alone.
- *Does it work without Docker?* Yes. When `QDRANT_URL` is empty, Qdrant runs embedded, on
  disk under `index/qdrant`.

## AS3.2 / AS4.2: When the system says "I don't know"

**The problem.** A technician asks about a Siemens PLC, or about a feature the ACS580 doesn't
have. Retrieval *always* returns something, the five nearest chunks, and some of them sound
on-topic. If we generate from those, we get a confident, well-cited, wrong answer. In this
product that's the worst possible failure.

**What the plan said:** one threshold on the retrieval score. **What we found:** it can't work.
`eval/results/calibrate_fused.txt` has the evidence. The fused score is rank arithmetic, so our
best answer (G01, fault 2330) scores exactly the same as a question about Caterpillar engine
bolts. Raw embedding similarity doesn't separate them either (an out-of-corpus question scored
0.84, a real one 0.74). And "which ACS580 firmware added EtherCAT redundancy" names the right
product in the right vocabulary. No score can refuse it; only reading the chunks can.

**What we built instead: two gates.**
1. **Retrieval gate:** refuse if retrieval finds nothing at all.
2. **Grounded gate:** the model reads the excerpts and must first decide `answerable`: do
   *these excerpts* answer *this* question? Then code (not the prompt) enforces it: every
   cited item must point at an excerpt the model was actually shown, and a safety warning must
   match the manual character for character. If nothing survives those checks, the user gets
   a refusal, even if the model said it could answer. Code: `generation/generate.py::generate`.

**The refusal itself** (`generation/refusal.py`) shows the 3 nearest passages with page
numbers, so the technician can look for themselves, and it has **no field for steps**. The
system can't give repair steps it can't cite, and that's enforced by the response type rather
than by asking the model to behave.

**Why this is the right trade.** Deciding answerability from evidence is exactly what the model
is good at, and it's the only approach that handles the hardest case (right product, missing
fact). The cost is one model call per question, which we already make.

**Still to measure (needs the API key):** do all 5 out-of-corpus questions refuse, while
none of the 25 gold questions do? Until that run exists, don't claim it.

## AS6.2 / AS6.3: The answer card and the evidence pane

**What the technician sees.** The safety warning comes first, in a yellow box with a heavy
border, so it can be found without reading anything else. Below it are labelled sections:
*What it means*, *Probable causes* (each tagged high/medium/low), *What to do* (numbered in
the manual's order) and *Tools and parts*. Every line ends in a page link (e.g. "p. 553").
Tap it and the exact region of the manual page appears inline, cropped to that table row or
paragraph. A field the manual doesn't support says "Not stated in the manual." rather than
being filled in.

**Why the crop is the headline feature.** Any chatbot can paste in a page number. Showing the
technician the actual row they're relying on, from the manufacturer's own page, is what makes
the answer checkable in five seconds on a phone.

**How we know the crops are right (the done-check: all gold questions, not a sample of 3).**
`tools/verify_crops.py` checks every chunk on every gold page, 396 of them, two ways: the PDF's
own text inside each crop box must match the chunk, and the page images must be exactly 150 dpi
renders. Result: **395 / 396 pass.** The one failure is an ingest defect on a diagram-callout
page (quickstart p4): its text came out garbled and its box points at a neighbouring block.
Three gold questions (G10, G11, G24) sit on the scanned manual, which isn't ingested yet (AS1.4).

**Likely question:** *"How do you map a citation to a region?"* Each chunk stores its bounding
box in PDF points at ingest. The server crops the pre-rendered 150 dpi page image to that box,
plus 6 pt of padding. No re-rendering happens per request, so it's fast on a phone.
