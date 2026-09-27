"""Chunk lookup and page-region cropping, per schema.md "Rendering a crop"."""
import io
import json
from pathlib import Path

from PIL import Image

from core.chunks import load_chunks  # noqa: F401  (re-exported for api.main)
from ingest.schema import Chunk

DPI = 150
SCALE = DPI / 72  # render pixels per PDF point
PAD = 6.0         # points, so a table row isn't cut through its glyphs


def crop_png(chunk: Chunk, pages_dir: Path) -> bytes:
    """Crop the chunk's bbox out of its page render. bbox is PDF points, origin bottom-left."""
    with Image.open(pages_dir / Path(chunk.source_image).name) as page:
        W, H = page.width / SCALE, page.height / SCALE
        x0, y0, x1, y1 = chunk.bbox
        x0, y0 = max(0.0, x0 - PAD), max(0.0, y0 - PAD)
        x1, y1 = min(W, x1 + PAD), min(H, y1 + PAD)
        box = (round(x0 * SCALE), round((H - y1) * SCALE), round(x1 * SCALE), round((H - y0) * SCALE))
        buf = io.BytesIO()
        page.crop(box).save(buf, format="PNG")
    return buf.getvalue()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
