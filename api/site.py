"""What the non-Ask pages show: the manual library and the measured results.

Everything here is read from files the pipeline already writes (chunks.jsonl,
eval/results/*.json), so a number on screen traces to a committed artifact.
"""
import json
from collections import Counter
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from core import config

RESULTS = config.ROOT / "eval" / "results"

# Human-facing catalogue of the corpus (corpus.md). doc_id is the PDF stem.
MANUALS = [
    ("acs580_firmware_manual", "ACS580 firmware manual", "ACS580", 632, "Parameters, fault and warning codes"),
    ("acs880_primary_firmware_manual", "ACS880 primary control program firmware manual", "ACS880", 690, "Parameters, fault and warning codes"),
    ("acs580_01_hardware_manual", "ACS580-01 hardware manual", "ACS580", 500, "Installation, wiring, frames R1–R9"),
    ("acs880_01_hardware_manual", "ACS880-01 hardware manual", "ACS880", 394, "Installation, wiring, technical data"),
    ("acs580_01_type4x_quickstart", "ACS580-01 Type 4X quick installation guide", "ACS580", 15, "Quick install and start-up"),
    ("acs580_technical_catalog", "ACS580 technical catalogue", "ACS580", 84, "Selection and rating tables"),
    ("fpno21_profinet_adapter_manual", "FPNO-21 PROFINET adapter manual", "ACS580 · ACS880 · ACQ580", 200, "Fieldbus option module"),
    ("acs550_to_acs580_replacement", "ACS550 → ACS580 replacement guide", "ACS550 → ACS580", 24, "Scanned. Needs OCR (AS1.4)"),
]

# Rows of the results table, in the order the pitch reads them.
RETRIEVERS = [
    ("baseline", "Baseline", "Raw PDF text, 500-character chunks, embeddings only"),
    ("bm25", "Keyword (BM25)", "Exact-word ranking over structured chunks"),
    ("dense", "Semantic (embeddings)", "Meaning-based search over structured chunks"),
    ("fused", "AskManual (fused)", "Keyword + semantic + exact fault-code lookup, rank-fused, scoped by product"),
]
COLUMNS = [("fault_code", "Fault codes"), ("table", "Tables"), ("prose", "Prose"),
           ("diagram", "Diagrams"), ("OVERALL", "Overall")]


@dataclass(frozen=True)
class Manual:
    doc_id: str
    title: str
    family: str
    pages: int
    scope: str
    chunks: int
    kinds: dict[str, int]

    @property
    def searchable(self) -> bool:
        return self.chunks > 0


@cache
def _chunk_counts() -> dict[str, Counter]:
    """chunk_type counts per doc, straight off chunks.jsonl. A host running on fixtures only
    has no chunks.jsonl; the page then lists the manuals without counts."""
    counts: dict[str, Counter] = {}
    if not config.CHUNKS_PATH.exists():
        return counts
    with config.CHUNKS_PATH.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                row = json.loads(line)  # two fields only: skip full schema validation for 35k rows
                counts.setdefault(row["doc_id"], Counter())[row["chunk_type"]] += 1
    return counts


def manuals() -> list[Manual]:
    counts = _chunk_counts()
    return [Manual(d, t, f, p, s, sum(counts.get(d, {}).values()), dict(counts.get(d, {})))
            for d, t, f, p, s in MANUALS]


def results(directory: Path = RESULTS) -> dict | None:
    """{"rows": [...], "columns": [...], "n": {...}} from eval/results, or None before any run."""
    rows = []
    for name, label, what in RETRIEVERS:
        path = directory / f"{name}.json"
        if not path.exists():
            continue
        table = json.loads(path.read_text(encoding="utf-8"))["table"]
        rows.append({"name": name, "label": label, "what": what,
                     "cells": {k: table[k]["hits"] / table[k]["n"] for k, _ in COLUMNS if k in table}})
    if not rows:
        return None
    first = json.loads((directory / f"{rows[0]['name']}.json").read_text(encoding="utf-8"))["table"]
    best = {k: max(r["cells"].get(k, 0) for r in rows) for k, _ in COLUMNS}
    return {"rows": rows, "columns": COLUMNS, "n": {k: first[k]["n"] for k, _ in COLUMNS if k in first},
            "best": best}
