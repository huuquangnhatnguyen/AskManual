# Chunk schema

A **chunk** is one retrievable unit: a paragraph, one row of a table, or one
figure. Every chunk is one line of `chunks.jsonl`, and every citation the app
shows resolves to exactly one chunk. The Pydantic model that enforces this is
`ingest/schema.py`; this file is the contract, that file is the check.

```json
{
  "chunk_id": "acs580_firmware_manual_p553_c007",
  "doc_id": "acs580_firmware_manual",
  "product_family": ["ACS580"],
  "page": 553,
  "bbox": [54.0, 515.1, 380.2, 522.9],
  "chunk_type": "table_row",
  "text": "2330 | Earth leakage | Drive has detected load unbalance ... | Check there are no power factor correction capacitors ...",
  "parent_section_id": "9.7",
  "parent_section_title": "Fault messages",
  "fault_codes": ["2330"],
  "source_image": "pages/acs580_firmware_manual_p0553.png"
}
```

## Fields

| Field | Type | What it is | What breaks if it is missing |
|---|---|---|---|
| `chunk_id` | string, `^[a-z0-9_]+$` | `{doc_id}_p{page}_c{n:03d}`, `n` = reading-order index of the chunk on that page, from 0. Stable across re-ingests of the same PDF. | Citations can't be resolved — `/evidence/{chunk_id}` has nothing to look up, and eval can't match retrieved chunks to gold pages. |
| `doc_id` | string | Filename stem of the PDF in `corpus/`, e.g. `acs580_firmware_manual`. | Can't open the source PDF to render or verify the chunk; gold matching (which keys on `doc_id` + `page`) fails. |
| `product_family` | list of strings, uppercase, ≥1 item | Drive families the *document* covers, from `corpus.md`. A list because `fpno21_profinet_adapter_manual` covers `ACS580`, `ACS880` and `ACQ580` at once. | Family scoping (M5) can't filter, so "fault 2310" returns ACS580 and ACS880 answers mixed — 168 codes are shared between the two firmware manuals. |
| `page` | int, ≥1 | **1-based PDF page index** — PyMuPDF's `page.number + 1`. Not the number printed on the page (the ACS580 firmware manual is offset by 2). | Nothing can be rendered or cited, and recall@k against `eval/data/gold.jsonl` (also 1-based index) is computed against the wrong page. |
| `bbox` | `[x0, y0, x1, y1]`, floats | Region of the chunk on its page, **PDF points (1/72 in), origin bottom-left, y up**, `x0<x1`, `y0<y1`. See *Coordinates* below. | The evidence pane can only show a whole page, not the line the claim came from — the core promise of the product. |
| `chunk_type` | enum | `prose` · `table_row` · `figure` · `heading` | Retrieval can't boost table rows for fault-code queries, and the UI can't tell a figure crop (show the image) from a text line (highlight). |
| `text` | string, non-empty | What gets embedded and BM25-indexed. `prose`: the paragraph. `table_row`: cells joined with ` \| `, header-labelled if the header is on the page. `figure`: the vision model's description plus any caption. | The chunk is unretrievable; for `safety_warning` the verbatim-copy test (AS4.1) has nothing to check against. |
| `parent_section_id` | string or null | Ordinal path of the nearest enclosing heading in the PDF outline (`doc.get_toc()`): count entries per level, join with dots. The outlines carry titles but no printed numbers, so this is derived, not read — `acs580_firmware_manual` p553 → `"9.7"` (*Fault messages*, starts p551). Null if the page precedes the first TOC entry. | Generation loses section context — a table row "2330 \| Earth leakage" is fed to the LLM without knowing it's in *Fault messages*. |
| `parent_section_title` | string or null | Title of that heading, as printed. | Same as above, and the UI can't show "Fault messages › p. 553" as a breadcrumb. |
| `fault_codes` | list of strings, may be empty | Every drive fault/warning code in the chunk: 4 hex characters (`2330`, `A2B1`, `7081`), normalised to uppercase. Populated from the code column for `table_row`, regex elsewhere. | Exact-code lookup degrades to BM25 alone, and "2330" can match a parameter value or page number instead of the fault. |
| `source_image` | string | Path, relative to the repo root, of the full-page render: `pages/{doc_id}_p{page:04d}.png` at **150 dpi**. For `figure` chunks it is still the page render; the figure's own crop is derived from `bbox`. | The crop has to be re-rendered from the PDF on every request, which is too slow for the scanned pages and impossible on a host without the corpus. |

## Coordinates

`bbox` is PDF user space: points, origin at the **bottom-left** of the page,
y increasing upward. That is what the PDF file itself uses, and it is **not**
what PyMuPDF reports — PyMuPDF's `Rect` is origin top-left, y down. Checked on
`acs580_firmware_manual` p553 (a 420 × 595 pt page): the word `2330` comes back
from `page.get_text("words")` as `(54.0, 72.1, 69.4, 79.9)`, and
`page.transformation_matrix` is `(1, 0, 0, -1, 0, 595)`.

Converting at ingest (`H` = `page.rect.height`):

```
bbox = [r.x0, H - r.y1, r.x1, H - r.y0]        # PyMuPDF Rect -> schema bbox
```

so that word is stored as `[54.0, 515.1, 69.4, 522.9]`.

## Rendering a crop from `page` + `bbox`

Everything needed is on the chunk. With `s = 150 / 72` (the render's pixels per
point) and `H` the page height in points (= image height in px ÷ `s`):

```
left   = x0 * s
top    = (H - y1) * s
right  = x1 * s
bottom = (H - y0) * s
crop   = Image.open(source_image).crop((left, top, right, bottom))
```

Pad by 6 pt on each side before cropping, clamped to the page, so a single
table row isn't cut through its glyphs. Pages with `/Rotate` set are rendered
upright by PyMuPDF; ingest must store `bbox` in the *unrotated* page's space
and `api/evidence.py` applies `page.rotation_matrix` — none of the eight
corpus PDFs has a rotated page today, so this is a guard, not a code path.

## Invariants (checked by `ingest/schema.py`)

- `chunk_id` starts with `{doc_id}_p{page}_c`
- `0 ≤ x0 < x1 ≤ page width`, `0 ≤ y0 < y1 ≤ page height`
- `chunk_type == "table_row"` ⇒ `text` contains ` | `
- `fault_codes` items match `^[0-9A-F]{4}$`
