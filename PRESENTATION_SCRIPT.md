# AskManual: presentation script (~6 min)

Deck: `AskManual_Final_Deck.pptx`. Timings are targets; the bold line on each slide is the one to land if you're running short.

---

**1. Title (15 s)**
Hi, I'm Nhat. This is AskManual: citation-backed troubleshooting for maintenance technicians. **The technician describes a fault, and the system answers and shows the exact region of the manual page the answer came from.**

**2. The problem (35 s)**
Picture a technician at a faulted drive. The line is stopped, the panel is open and they're holding a phone. The answer is in the manual, but the manual runs to 600 pages. And the answer usually isn't in a paragraph. It's one row in a fault-code table, or a region of a wiring diagram, or a scanned page. Generic search returns the document, not the answer. **Search fails exactly where maintenance answers live: in tables, diagrams and scans.**

**3. The solution (30 s)**
The input is the symptom in plain language, plus a fault code or drive family if they have one. Naming the family matters. An ACS580 fault answered from the ACS880 manual is wrong even when the words match. The output isn't four sentences of chat. It's a structured card: what the fault means, ranked causes, ordered steps, and tools and parts. Safety warnings are copied word for word. **Every line is cited to a page and to the region of that page.**

**4. How one question is answered (45 s)**
Here's one real question, from start to finish: "My ACS580 is showing fault 2330. What do I check?" First, the system picks out the code, 2330, and the drive, ACS580. Second, it searches only the ACS580 manuals, three ways at once: by exact code, by keyword and by meaning. Third, the passages the searches agree on rise to the top, and it keeps the best five. Fourth, and this is the important one, it checks whether those passages really answer the question. Fifth, if they do, you get the card: the safety warning first, then causes and steps, each with its page. **Tap "p. 553" and you see the actual row from ABB's manual. If they don't, it says so and shows the three closest pages instead of guessing.**

**5. Technical approach (50 s)**
It comes in two halves. Offline, we parse 8 ABB manuals with a layout-aware parser. That's 2,539 pages. Table rows stay whole, fault codes get tagged, and every chunk keeps its page and bounding box. That box is what makes visual citation possible, and you can't get it back if you throw it away at parse time.
At request time there are three retrieval lanes: BM25 for exact words, dense embeddings for meaning, and an exact fault-code lookup. Reciprocal Rank Fusion merges them using only their ranks. Then a grounded gate decides whether to answer or refuse. **To an embedding, fault 2330 is just a number, which is why the code lane exists.**

**6. What makes it different (50 s)**
Three decisions. One: fault codes get their own lane, because they're the main use case and what embeddings handle worst. That took fault-code recall from 1 in 6 to 6 in 6.
Two: visual citation. Tap any line and you see the cropped table row from ABB's own page. We checked every chunk on every gold page, and 395 of 396 crops match their text.
Three: refusal. Our plan was a score threshold, but we measured it and it can't work. An out-of-scope question scored the same as our best answer. So the model first has to judge whether the excerpts actually answer the question. Code then checks every citation and every verbatim warning, and a refusal has no field for steps. **A confident wrong answer about a live 480-volt panel is worse than no answer.**

**7. Results (60 s)**
25 gold questions, each with a hand-checked source page, run against a naive baseline and against our pipeline. Overall recall@5 went from 0.36 to 0.56. The big gain is fault codes, from 0.17 to 1.00, and table rows go from 0.29 to 0.43.
I'll point out the weak spots myself. Diagrams got worse, 0.50 down to 0.33, because I cut figure ingestion. The three scanned-manual and three cross-manual questions score zero for every retriever, because there's no OCR yet. n is 25, so one question moves a row by about 0.15, and these numbers are directional. Citation accuracy and out-of-corpus refusal haven't been measured end to end yet. **Big win where it matters most, and every number comes from a committed results file.**

**8. Trade-offs (35 s)**
Eight manuals rather than fifty, so every gain is measured. Hybrid over dense-only: it costs a second index and buys the fault-code queries. I cut photo entry, OCR, figures and a knowledge graph to get visual citation and the refusal gate done properly. And one thing I didn't ship: lowering BM25's length penalty gave the same 0.56 on its own, but I'd picked it by looking at the test questions, which is tuning on the test set. **I'd rather report a number I can defend.**

**9. Roadmap (30 s)**
What's built: ingestion, three-lane retrieval, cited answers with crops, grounded refusal, a phone-width UI, and 64 passing tests. What comes next: OCR, figures, nameplate photos and citation-accuracy measurement. After that, live telemetry, so the fault code comes from the machine, and technician feedback, so the fix that actually worked becomes a source. **The long-term vision is the layer where fault state, documentation and a retiring workforce's knowledge meet.**

**10. Close (15 s)**
**An answer is only useful if the technician can trust it.** So the system retrieves the fault-code row, shows the page region, refuses when the manuals don't cover the question, and is measured against a baseline. Thank you.

---

## Likely questions (short answers)

- **Why k=60?** It's the constant from the original RRF paper (Cormack 2009). We didn't tune it.
- **No fault code in the question?** The code lane returns nothing and fusion runs on BM25 and dense.
- **How does a citation become a crop?** The chunk stores its bbox in PDF points at ingest, and the server crops the pre-rendered 150 dpi page. Nothing is re-rendered per request.
- **Is the scanned manual real?** It's constructed. ABB's public library has no truly scanned manuals, so we rasterised one at 200 dpi. That's easier than a real scan, and the README says so.
- **Is there a public URL?** Not yet. It runs locally with `docker compose up`, and deployment is a known gap.
