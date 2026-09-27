"""AS4.1 — retrieved chunks -> the M4 answer, every field traceable, nothing invented.

Two steps, kept separate so the second is testable without a model call:
    draft    = llm.structured(SYSTEM, user_message(q, chunks), Draft)   # what the model says
    answer   = finalize(draft, chunks)                                  # what we are willing to show
"""
from typing import Literal

from pydantic import BaseModel

from api.models import Answer, Cause, Cited, Refusal, SafetyWarning, Source, Step
from generation import llm
from generation.prompt import SYSTEM, user_message
from generation.refusal import refuse
from ingest.schema import Chunk


# The model's output schema: the Answer minus `kind` and `sources`, which we fill ourselves.
# Kept free of length/range constraints — structured outputs support only a subset of JSON Schema.
class DCited(BaseModel):
    text: str
    cite: str


class DCause(DCited):
    likelihood: Literal["high", "medium", "low"]


class DStep(DCited):
    n: int


class DWarning(BaseModel):
    verbatim: str
    cite: str


class Draft(BaseModel):
    # The grounded refusal gate (see generate()). First, so the model decides it before writing fields.
    answerable: bool = True
    fault_meaning: DCited | None
    probable_causes: list[DCause]
    corrective_steps: list[DStep]
    tools_and_parts: list[DCited]
    safety_warning: DWarning | None


def finalize(draft: Draft, chunks: list[Chunk]) -> Answer:
    """Turn a draft into an Answer we can stand behind:
      - drop any item whose `cite` is not one of `chunks` (the model cited something it wasn't shown)
      - drop `safety_warning` unless `verbatim` appears character-for-character in its cited chunk
      - renumber corrective steps 1..n after drops
      - build `sources` from exactly the cites that survived
    """
    shown = {c.chunk_id: c for c in chunks}

    def keep(item) -> bool:
        return item.cite in shown and bool(item.text.strip())

    meaning = draft.fault_meaning
    steps = sorted((s for s in draft.corrective_steps if keep(s)), key=lambda s: s.n)
    warning = draft.safety_warning
    if warning and not (warning.cite in shown and warning.verbatim.strip()
                        and warning.verbatim in shown[warning.cite].text):
        warning = None

    fields = dict(
        fault_meaning=Cited(text=meaning.text, cite=meaning.cite) if meaning and keep(meaning) else None,
        probable_causes=[Cause(text=c.text, cite=c.cite, likelihood=c.likelihood)
                         for c in draft.probable_causes if keep(c)],
        corrective_steps=[Step(n=i, text=s.text, cite=s.cite) for i, s in enumerate(steps, start=1)],
        tools_and_parts=[Cited(text=t.text, cite=t.cite) for t in draft.tools_and_parts if keep(t)],
        safety_warning=SafetyWarning(verbatim=warning.verbatim, cite=warning.cite) if warning else None,
    )
    items = [fields["fault_meaning"], *fields["probable_causes"], *fields["corrective_steps"],
             *fields["tools_and_parts"], fields["safety_warning"]]
    cited = dict.fromkeys(i.cite for i in items if i is not None)  # ordered, unique
    sources = {cid: Source(doc_id=shown[cid].doc_id, page=shown[cid].page, chunk_type=shown[cid].chunk_type,
                           parent_section_title=shown[cid].parent_section_title)
               for cid in cited}
    return Answer(**fields, sources=sources)


def is_empty(answer: Answer) -> bool:
    """Nothing a technician could act on survived finalize. A lone safety warning isn't an answer."""
    return not (answer.fault_meaning or answer.probable_causes or answer.corrective_steps or answer.tools_and_parts)


def generate(question: str, chunks: list[Chunk]) -> Answer | Refusal:
    """The second refusal gate. Retrieval always finds *something* on-topic-sounding, so whether
    the excerpts actually answer the question is decided by reading them: the model says so in
    `answerable`, and if nothing cited survives finalize we refuse regardless of what it said."""
    draft = llm.structured(SYSTEM, user_message(question, chunks), Draft)
    if not draft.answerable:
        return refuse(chunks)
    answer = finalize(draft, chunks)
    return refuse(chunks) if is_empty(answer) else answer
