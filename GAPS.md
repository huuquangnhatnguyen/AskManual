# AskManual — gap audit (2026-09-27, 20:25 UTC)

Measured against the goals in MILESTONES.md. Submit target is **17:00 ET (21:00 UTC)**, hard close 21:59 UTC.
At the time of this audit that left **~35 min to the target and ~1.5 h to the hard close.**

## What's actually done (verified, not taken from the status column)

- Corpus, schema, 25 gold questions + 5 out-of-corpus (`eval/data/`)
- Ingest: 35,742 chunks (prose / table_row / heading) + 2,539 page renders
- Retrievers: baseline, bm25, dense, fused (RRF k=60 + fault-code lane + family scope), each with a result file in `eval/results/`
- Fused recall@5 **0.56 vs baseline 0.36**; fault_code 6/6 vs 1/6
- Generation: `finalize`, grounded gate and verbatim-safety check are implemented; refusal is implemented
- API: `/ask`, `/identify` (stub), `/evidence/{id}`, `/health`, phone-width UI, answer card, evidence crop (395/396 crops verified)
- `pytest`: **64 passed, 0 pending skips**
- README, DEVELOPING, PRESENTER_NOTES written

## Missing: blocks the submission

| # | Gap | Evidence | Goal it breaks |
|---|---|---|---|
| 1 | **Nothing is committed.** Only commit is `79adaf9` (scaffold). All of `api/`, `retrieval/`, `generation/`, `tests/`, the README etc. are untracked. | `git status` | "source code" deliverable, AS7.1 freeze tag |
| 2 | **No remote and no public repo.** `git remote -v` is empty and `gh` isn't installed. | | AS8.4 "repo is public" |
| 3 | **No public URL.** No Railway CLI, no domain recorded anywhere, no deploy trace. AS0.7 and AS0.8 were never done. | `which railway` fails | Headline delivery: "a public HTTPS URL a judge can open on a phone" |
| 4 | **No demo video.** | No .mp4/.mov found | AS8.1 deliverable |
| 5 | **No deck.** No .pptx or deck file under `C:\CLAUDE-LOCAL`. | | AS8.3 deliverable ("presentation deck") |
| 6 | **Real answers never produced end to end.** `ANTHROPIC_API_KEY` is not set in `.env`, and there is no `eval/results/fused_answers.json`. | `.env` keys: DATABASE_URL, QDRANT_URL, POSTGRES_PASSWORD only | AS4.3, and the video's steps 2–4 |

## Missing: claims you can't make yet

| Gap | Consequence |
|---|---|
| Citation accuracy never measured (`cite_ok` is 0 in every file because `--answers` was never run) | The results table only has recall@5. Half of the metric pair in AS2.1/AS7.2 is empty |
| Out-of-corpus refusal never measured with the grounded gate. The score threshold is proven inseparable (`calibrate_fused.txt`) | You can't claim "5/5 refuse, 0/25 gold refuse". PRESENTER_NOTES already says not to |
| No freeze tag, and result files aren't committed | AS7.2 rule: "a number not in a committed file doesn't exist" |
| `build_fault_codes` (Postgres) still raises `NotImplementedError` (`retrieval/index.py:78`) | `retrieval.index` can't print three `ok` lines. The code lane reads `chunks.jsonl` instead, so retrieval isn't affected, but the AS2.3 done-check fails and the README's stage 2 says "must end with three ok lines" |

## Missing: known scope holes (state them plainly, don't fix today)

- **AS1.4 OCR:** the scanned manual `acs550_to_acs580_replacement` has **0 chunks**. 3 scanned and 3 cross_manual gold questions score 0.00 on every retriever.
- **AS1.3 figures:** no `figure` chunks exist. Diagram recall is 0.33, below the baseline's 0.50.
- **M5 photo entry:** cut. `/identify` is a stub. **The video script's step 1 ("Photograph the fault") has nothing real behind it**, so the script needs to change.
- **AS8.5 reproducible run:** there's no published index artifact. `pages/` is 414 MB and `index/` is 171 MB, both git-ignored. A clean clone can only run fixture mode.
- One crop fails (quickstart p4, garbled ingest).

## Docs that are out of date

- MILESTONES status column: AS0.5 and AS0.6 still say TODO and AS2.1 says TODO, but all three exist and pass. AS4.1 and AS4.2 say DOING, but their tests pass.
- DEVELOPING.md "Current numbers" still quotes the `keyword` stand-in (0.44), not fused 0.56.
- README stage 3b says to set `REFUSAL_THRESHOLD` from calibrate, but calibrate proved a threshold can't separate the sets.

## Triage for the time left

Before 21:00 UTC, in this order:
1. `git add` + commit everything (check `.env` stays ignored; it does), tag `freeze`, create a GitHub repo, push, make it public. ~10 min
2. Put a key in `.env`, then run `PIPELINE=real` locally and ask G01 + one out-of-corpus question. This is the footage for the video. ~5 min
3. Record the phone video against **localhost or a screen recording**. Skip the photo step and show typed question → card → crop → refusal → results table. ~15 min
4. Deck: one results slide from the PRESENTER_NOTES table (recall@5 only; say citation accuracy wasn't measured). ~10 min
5. Submit. Put the no-public-URL limitation in the README rather than leaving it unstated.

A Railway deploy with a 414 MB image (build, push to GHCR, index the remote Qdrant) won't fit before 21:00. Try it only after submitting, if the form accepts edits before 21:59.
