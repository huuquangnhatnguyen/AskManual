# tools/

Scripts that read the corpus. Run them, do not rewrite them.

All of them print page numbers as **1-based PDF page indexes**, which is what the
parser reports and what `bbox` and `source_image` are relative to. That is the
number that belongs in `eval/data/gold.jsonl`. It is not always the number printed
on the page — the ACS580 firmware manual runs an offset of 2. See `corpus.md`.

| Script | Does | Usage |
|---|---|---|
| `pdfgrep.py` | Regex search across `corpus/*.pdf`, printing `doc p<page> line`. | `python tools/pdfgrep.py "2330" acs580_firmware --ctx 5` |
| `pdfpage.py` | Print the full text of given pages of one document. | `python tools/pdfpage.py acs580_firmware 553 554` |
| `inventory.py` | Page count, size, text volume and top-level TOC for every corpus PDF. Regenerates the table in `corpus.md`. | `python tools/inventory.py` |
| `verify_gold.py` | Opens the page each `eval/data/gold.jsonl` entry cites and checks the answer's content words are actually on it. Reads `corpus/_digital/<doc>.pdf` instead when one exists (the flattened scan has no text). Non-zero exit on failure, so it can gate a commit. | `python tools/verify_gold.py` |
| `flatten_scan.py` | Rasterises one corpus PDF into an image-only "scan", moving the original to `corpus/_digital/`. Used once, for AS0.1. | `python tools/flatten_scan.py acs550_to_acs580_replacement` |
| `verify_crops.py` | AS6.3 gate. For every chunk on every gold page: checks the PDF text inside its `bbox` matches the chunk (catches a wrong y-flip or offset) and that `pages/*.png` is the page at 150 dpi (catches wrong crop scale). Crops the best chunk per gold question with the same `crop_png` `/evidence` serves, into a contact sheet. Non-zero exit on any failure. | `python tools/verify_crops.py` → `index/crop_check/index.html` |
| `make_api_fixtures.py` | Rebuilds `api/fixtures/chunks.jsonl` and its two page renders from the ACS580 firmware manual — the chunks the stubbed `/ask` cites and `/evidence` crops. | `python tools/make_api_fixtures.py` |

Windows note: anything printing page text needs
`sys.stdout.reconfigure(encoding="utf-8")` or it dies on the first non-cp1252
character. All four already do.

Dependency: `pymupdf` (installed). `pdftotext` is available and used only for
the AS0.1 no-text-layer check.
