"""AS4.2 — what /ask returns when it won't answer: retrieval found nothing (AS3.2), or the
model read the excerpts and they don't answer the question (generation.generate).

A message plus the top 3 chunks the system did find, with pages, so the technician can
look for themselves. No corrective steps of any kind — the Refusal model has no field
for them, so this is enforced by construction, not by wording.
"""
from api.models import Nearest, Refusal
from ingest.schema import Chunk

MESSAGE = "I couldn't find this in the manuals I have."
PREVIEW_CHARS = 240  # phone-sized; the full chunk is one tap away via /evidence


def preview(text: str, limit: int = PREVIEW_CHARS) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def refuse(nearest: list[Chunk]) -> Refusal:
    return Refusal(message=MESSAGE, nearest=[
        Nearest(chunk_id=c.chunk_id, doc_id=c.doc_id, page=c.page, text=preview(c.text))
        for c in nearest[:3]
    ])
