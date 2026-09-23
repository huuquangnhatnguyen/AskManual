# Corpus

Eight ABB low-voltage AC drive documents, all pulled from ABB's public library
(`library.abb.com`) on 2026-09-21 and 2026-09-22. **2,539 pages, 204 MB.**

Deliberately one machine *type* (LV AC drives) across **two product families**.
A single family would have made `product_family` a constant and left M5's
nameplate scoping with nothing to disambiguate. Two families that share almost
all of their vocabulary — both have a fault table, a DC link, an STO input, a
terminal diagram — is what makes the naive baseline in M2 fail in an
interesting way rather than a trivial one.

| File | Product family | Pages | Size | Kind | ABB doc ID |
|---|---|---|---|---|---|
| `acs880_primary_firmware_manual.pdf` | ACS880 | 690 | 7.8 MB | Firmware / parameters / fault tracing | 3AUA0000085967 Rev Y |
| `acs580_firmware_manual.pdf` | ACS580 | 632 | 11.2 MB | Firmware / parameters / fault tracing | 3AXD50000016097 Rev J |
| `acs580_01_hardware_manual.pdf` | ACS580 | 500 | 89.7 MB | Hardware, frames R1–R9 | 3AXD50000044794 Rev G |
| `acs880_01_hardware_manual.pdf` | ACS880 | 394 | 47.8 MB | Hardware | 3AUA0000078093 Rev V |
| `fpno21_profinet_adapter_manual.pdf` | **multi** (ACS580/ACS880/ACQ580) | 200 | 8.4 MB | Fieldbus option module | 3AXD50000158614 Rev E |
| `acs580_technical_catalog.pdf` | ACS580 | 84 | 39 MB | Catalogue / selection tables | ACS580-PHTC01U-EN Rev M |
| `acs550_to_acs580_replacement.pdf` | ACS550 → ACS580 | 24 | 4.2 MB | Comparison / replacement guide | 3AXD50000660681 Rev D |
| `acs580_01_type4x_quickstart.pdf` | ACS580 | 15 | 3.5 MB | Quick install & start-up (NA / UL) | 3AXD50001020156 Rev C |

## The three added on 2026-09-22

The first five were the deliberate ceiling the charter set. These three were
added to close measurement gaps the gold set exposed, not to grow the corpus
for its own sake.

**`acs880_primary_firmware_manual.pdf` — the important one.** Before it, all
six `fault_code` gold questions lived in a single document, so that query type
was trivially easy: there was only one place in the corpus where fault codes
existed at all, and a retriever could score well by accident. The two firmware
manuals now **share 168 four-character codes**, including real faults 2281,
2310 and 2330. "What is fault 2310?" is genuinely ambiguous without knowing
the drive family, which is what makes `product_family` scoping load-bearing
and gives M5's nameplate photo real work to do. It also has the deepest
heading tree in the corpus — 2,508 TOC entries — so it is the best test of
`parent_section_id` extraction.

**`acs580_technical_catalog.pdf`** brings a table shape nothing else has:
multi-column selection and rating matrices rather than the row-per-fault and
row-per-terminal tables in the manuals. It also overlaps the hardware manual
on ratings for the same drives in a different layout, which is a deliberate
cross-document tension. 170 raster images in 84 pages — by far the most
image-dense document here.

**`fpno21_profinet_adapter_manual.pdf`** is the edge case. ABB's library files
it under ACS580, ACS880 *and* ACQ580 simultaneously: it belongs to no single
product family. `schema.md` assumes one `product_family` per document, so this
one breaks the assumption, and AS5.2's scoped retrieval will either drop it or
mis-scope it. Better found now than during the demo.

**Not yet reflected in the gold set.** All 25 questions still target the
original five documents, and `verify_gold.py` is green at 25/25. By the
charter's own rule — *"every additional manual needs its own gold questions,
or it contributes nothing measurable"* — these three contribute nothing to the
metrics until roughly 10–12 questions are written against them. Until then
they add ingest surface and retrieval distractors but no measurement.

Re-fetch any of them with:

```bash
curl -L -o out.pdf "https://search.abb.com/library/Download.aspx?DocumentID=<ID>&LanguageCode=en&DocumentPartId=1&Action=Launch"
```

Documents whose library entry shows no `PART` field need `DocumentPartId=`
(empty) instead of `1`, or the endpoint returns 404.

## Scanned manual — open, and why

**AS0.1 is not satisfied on this point yet.** It asks for at least one
genuinely scanned PDF with no text layer, verified by `pdftotext` printing
nothing. ABB's public library does not appear to contain one. Checked and
rejected:

| Candidate | Year | Result |
|---|---|---|
| ACS600 MultiDrive Modules Installation Manual (3BFE64119010) | 2003 | 76,697 text chars — born-digital |
| ACS600 MultiDrive Hardware Manual (3AFY63700118) | 2003 | 89,292 chars — born-digital |
| ACS600 PFC Firmware Manual (3AFY61279008) | 2003 | 246,417 chars — born-digital |
| ACS600 Standard App 6.x Firmware Manual (3AFY61201441) | 2003 | 323,664 chars — born-digital |
| User's Manual ACS 502-506 (literal-string doc ID, 1990s drive) | 2014 upload | 158,466 chars — born-digital |

A structural check with PyMuPDF confirms it: zero full-page images in any of
them. ABB appears to have re-typeset rather than scanned its back catalogue.

The remaining options, in preference order:

1. **Flatten `acs550_to_acs580_replacement.pdf` into an image-only PDF.**
   24 pages, so it is the cheapest to OCR, and its ACS550 comparison data
   appears nowhere else in the corpus — so a question against it genuinely
   tests the OCR path rather than being answerable from a sibling manual.
   `pdftotext` then prints nothing, which is AS0.1's acceptance test verbatim.
   Record it here as constructed, not found, so AS8.2 stays honest.
2. Source a scan from outside ABB's library — uncertain provenance.
3. Amend AS0.1 and AS1.4 to drop OCR from the prototype.

Three gold questions (G10, G11, G24) already target that document exclusively
and carry `scan_target: true`, so whichever route is taken they need no
rewriting.

## Things the ingest pipeline has to handle

Found while building the gold set. Each one is cheap to fix now and expensive
to discover on D8.

- **Page-number offset differs per document.** `acs580_firmware_manual` prints
  page "555" on PDF page 553 — an offset of 2. `acs580_01_hardware_manual`
  prints "310" on PDF page 310 — offset 0. Cross-references inside the text
  ("see page 310") use the *printed* number. `gold.jsonl` stores the PDF index
  in `page` and the printed number separately in `printed_page`.
- **Fault codes are 4-character hex, not `Fxxxx`.** Real ACS580 codes are
  `2310`, `3210`, `7122`; warnings are `A2B1`, `A5A0`. The `F0001` in the
  `schema.md` example and in AS2.3's acceptance test
  (`WHERE code = 'F0001'`) is ACS550-era format and matches nothing in this
  corpus. Both need updating before AS1.2 and AS2.3 are written.
- **Aux codes share the code column.** Inside a fault entry, sub-rows like
  `0001`, `0002`, `0080` are auxiliary codes belonging to the fault above
  them, not separate faults. A naive row extractor will emit them as
  top-level fault codes.
- **Private Use Area characters.** Symbol-font bullets arrive as `` and
  similar. Strip or normalize them, or they end up in the embeddings.
- **Figures are vector art, not embedded images.** This is the one most
  likely to cost a milestone. Across the original five documents there are
  386 raster images in 1,565 pages, and **zero** on the diagram pages
  themselves: ACS580 hardware p238 has 0 raster images and 506 vector drawing
  operations; quickstart p4 has 0 and 7,951. AS1.3 as written — *"each
  detected figure produces a cropped PNG"* — finds nothing if detection means
  scanning for embedded images, which would leave all six `diagram` gold
  questions unanswerable and break AS6.3's citation crop. Figure detection
  has to cluster vector drawing bounding boxes (`page.get_drawings()`) into
  regions and render that rect, which is a different job than the 3h
  estimate assumes. The technical catalog is the exception: 170 raster
  images in 84 pages.
- **A handful of pages have no text layer even in these digital PDFs** —
  11 in the ACS580 hardware manual, 10 in the ACS880, 3 in the firmware
  manual. These are full-page graphics and need the AS1.3 vision path, not
  the text path.
- **Console encoding.** Any tool that prints page text needs
  `sys.stdout.reconfigure(encoding="utf-8")` on Windows or it dies on the
  first non-cp1252 character.
