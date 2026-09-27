"""Turn one corpus PDF into an image-only "scanned" PDF, for AS0.1 / AS1.4.

ABB's library has no genuinely scanned manual (see corpus.md), so one is
constructed: every page rasterised to greyscale JPEG at 200 dpi and re-wrapped
as a PDF with no text layer. `pdftotext` then prints nothing for it.

The born-digital original moves to corpus/_digital/, where verify_gold.py
reads it — the gold answers are checked against text the scan no longer has.
Page count and page size are unchanged, so gold page numbers still hold.

Run:  python tools/flatten_scan.py acs550_to_acs580_replacement
Idempotent: refuses if the original has already been moved aside.
"""
import shutil
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
DPI = 200


def main(doc_id: str) -> int:
    src = ROOT / "corpus" / f"{doc_id}.pdf"
    keep = ROOT / "corpus" / "_digital" / f"{doc_id}.pdf"
    if keep.exists():
        print(f"already flattened: original is at {keep.relative_to(ROOT)}")
        return 1
    keep.parent.mkdir(exist_ok=True)
    shutil.move(src, keep)

    digital = pymupdf.open(keep)
    scan = pymupdf.open()
    for page in digital:
        pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY)
        out = scan.new_page(width=page.rect.width, height=page.rect.height)
        out.insert_image(out.rect, stream=pix.tobytes("jpeg", jpg_quality=70))
    scan.save(src, garbage=4, deflate=True)
    chars = sum(len(p.get_text().strip()) for p in pymupdf.open(src))
    print(f"{src.relative_to(ROOT)}: {len(scan)} pages, {src.stat().st_size / 1e6:.1f} MB, {chars} text chars")
    return 0 if chars == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
