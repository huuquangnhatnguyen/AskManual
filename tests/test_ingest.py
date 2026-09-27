"""AS1.1 / AS1.2 checks. Run: pytest tests/

The corpus is not in git, so tests that open a PDF skip without it.
"""
import json
from collections import Counter
from pathlib import Path

import pymupdf
import pytest

from ingest.parse import parse_document, parse_page, survey
from ingest.sections import SectionIndex
from ingest.tables import table_rows, usable
from ingest.text import clean, codes_in_prose

CORPUS = Path("corpus")
FW = CORPUS / "acs580_firmware_manual.pdf"
needs_corpus = pytest.mark.skipif(not FW.exists(), reason="corpus/ not present")


def test_clean_strips_symbol_font_and_rejoins_hyphenation():
    assert clean("Warnings and\n faults") == "Warnings and faults"
    assert clean("insu-\nlation") == "insulation"


def test_prose_fault_codes_need_context():
    assert codes_in_prose("Drive trips on fault 2330 at start") == ["2330"]
    assert codes_in_prose("see warning A2B1 and A5A0") == ["A2B1", "A5A0"]
    assert codes_in_prose("set 1000 rpm, published 2019, page 2330") == []
    assert codes_in_prose("FACE BEAD CAFE") == []


@needs_corpus
def test_section_uses_position_when_a_page_opens_several_sections():
    with pymupdf.open(FW) as doc:
        idx = SectionIndex(doc)
    assert idx.at(535, 221.5) == ("9.2", "Safety")              # the WARNING under "Safety"
    assert idx.at(535, 140.0) == ("9.3.1", "Warnings and faults")
    assert idx.at(553, 500.0) == ("9.7", "Fault messages")


@needs_corpus
def test_fault_row_is_one_chunk_with_its_aux_codes_merged():
    with pymupdf.open(FW) as doc:
        page = doc[552]
        rows, carry = table_rows([t for t in page.find_tables().tables if usable(t)], None)
    fault_2330 = [r for r in rows if "2330" in r.fault_codes]
    assert len(fault_2330) == 1
    assert "0001" in fault_2330[0].text and "0080" in fault_2330[0].text
    assert not any(c in r.fault_codes for r in rows for c in ("0001", "0002", "0080"))
    assert carry == "3181"


@needs_corpus
def test_running_header_is_not_a_chunk():
    with pymupdf.open(FW) as doc:
        furniture, body = survey(doc)
        pieces, _ = parse_page(doc[552], furniture, body, None)
    assert not any(p.text.startswith("Fault tracing") for p in pieces)


@needs_corpus
def test_every_chunk_of_a_document_is_schema_valid():
    stats = Counter()
    with pymupdf.open(CORPUS / "acs580_01_type4x_quickstart.pdf") as doc:
        chunks = [c for _, cs in parse_document(doc, "acs580_01_type4x_quickstart", ["ACS580"], stats) for c in cs]
    assert chunks and stats["table_row"] > 0
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))


@pytest.mark.skipif(not Path("chunks.jsonl").exists(), reason="run python -m ingest.run corpus/ first")
def test_as12_2330_is_a_single_row_level_chunk():
    with open("chunks.jsonl", encoding="utf-8") as f:
        hits = [c for c in map(json.loads, f)
                if c["doc_id"] == "acs580_firmware_manual" and "2330" in c["fault_codes"]]
    assert [c["chunk_type"] for c in hits] == ["table_row"]


QS = CORPUS / "acs580_01_type4x_quickstart.pdf"


@needs_corpus
def test_diagram_callout_frame_is_not_a_table():
    # Quickstart p4: a stray diagram rule splits the right-hand callout paragraph into a fake
    # 2-column "table", clipping words at the split ("nsulated", "rive's"). Its text must come
    # through as intact prose, and every chunk's text must lie inside its own bbox.
    import sys
    sys.path.insert(0, "tools")
    from verify_crops import check_chunk

    with pymupdf.open(QS) as doc:
        chunks = [c for n, cs in parse_document(doc, "acs580_01_type4x_quickstart", ["ACS580"], Counter())
                  for c in cs if n == 4]
        page = doc[3]
        text = " ".join(c.text for c in chunks)
        import re
        assert not re.search(r"\b(nsulated|rive's|istribution|onduit)\b", text)  # words clipped at a fake column edge
        assert "For a conduit installation see a and b." in text
        bad = [(c.chunk_id, round(check_chunk(page, c), 2)) for c in chunks if check_chunk(page, c) < 0.7]
    assert bad == []


HW = CORPUS / "acs580_01_hardware_manual.pdf"


@needs_corpus
def test_table_with_clipped_header_keeps_its_rows_unprefixed():
    # Firmware p98, PFC macro terminals: a phantom column cuts the header "X1 Reference voltage…"
    # and a few spanning sub-headings. The terminal rows are real and must survive, without the
    # clipped "eference…:" label glued to each one.
    with pymupdf.open(FW) as doc:
        furniture, body = survey(doc)
        pieces, _ = parse_page(doc[97], furniture, body, None)
    rows = [p.text for p in pieces if p.kind == "table_row"]
    assert len(rows) > 30
    assert "1 | SCR | Signal cable shield (screen)" in rows
    assert not any("eference" in r.replace("Reference", "") for r in rows)


@needs_corpus
def test_framed_warning_box_is_one_intact_prose_chunk():
    # Hardware p207: a WARNING frame the finder split into two columns ("WA … | RNING"). The answer
    # card quotes warnings verbatim from chunk text, so a split warning can't be quoted at all.
    with pymupdf.open(HW) as doc:
        furniture, body = survey(doc)
        pieces, _ = parse_page(doc[206], furniture, body, None)
    warnings = [p for p in pieces if p.text.startswith("WARNING")]
    assert warnings and warnings[0].kind == "prose"
    assert "WARNING If you install IP66 (UL Type 4X) drive indoors or outdoors" in warnings[0].text
