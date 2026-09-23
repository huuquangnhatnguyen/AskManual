# tools/

Scripts that read the corpus. Run them, do not rewrite them.

All three print page numbers as **1-based PDF page indexes**, which is what the
parser reports and what `bbox` and `source_image` are relative to. That is the
number that belongs in `eval/data/gold.jsonl`. It is not always the number printed
on the page — the ACS580 firmware manual runs an offset of 2. See `corpus.md`.

| Script | Does | Usage |
|---|---|---|
| `pdfgrep.py` | Regex search across `corpus/*.pdf`, printing `doc p<page> line`. | `python tools/pdfgrep.py "2330" acs580_firmware --ctx 5` |
| `pdfpage.py` | Print the full text of given pages of one document. | `python tools/pdfpage.py acs580_firmware 553 554` |
| `inventory.py` | Page count, size, text volume and top-level TOC for every corpus PDF. Regenerates the table in `corpus.md`. | `python tools/inventory.py` |
| `verify_gold.py` | Opens the page each `eval/data/gold.jsonl` entry cites and checks the answer's content words are actually on it. Non-zero exit on failure, so it can gate a commit. | `python tools/verify_gold.py` |

Windows note: anything printing page text needs
`sys.stdout.reconfigure(encoding="utf-8")` or it dies on the first non-cp1252
character. All four already do.

Dependency: `pymupdf` (installed). `pdftotext` is available and used only for
the AS0.1 no-text-layer check.
