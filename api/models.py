"""The API contract, as Pydantic models. api/CONTRACT.md is the prose version.

The /ask response shape is fixed here, in AS0.5, before anything produces it:
AS4.3 swaps the fixture for the real pipeline and must not change these.
"""
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    product_family: str | None = None


class Cited(BaseModel):
    text: str = Field(min_length=1)
    cite: str


class Cause(Cited):
    likelihood: Literal["high", "medium", "low"]


class Step(Cited):
    n: int = Field(ge=1)


class SafetyWarning(BaseModel):
    verbatim: str = Field(min_length=1)
    cite: str


class Source(BaseModel):
    """What the UI needs to label a citation without a second request."""
    doc_id: str
    page: int = Field(ge=1)
    chunk_type: Literal["prose", "table_row", "figure", "heading"]
    parent_section_title: str | None


class Answer(BaseModel):
    """The M4 answer. A field the retrieved chunks don't support is null or [] — never invented."""
    kind: Literal["answer"] = "answer"
    fault_meaning: Cited | None
    probable_causes: list[Cause]
    corrective_steps: list[Step]
    tools_and_parts: list[Cited]
    safety_warning: SafetyWarning | None
    sources: dict[str, Source]

    def cites(self) -> list[str]:
        out = [c.cite for c in [*self.probable_causes, *self.corrective_steps, *self.tools_and_parts]]
        if self.fault_meaning:
            out.append(self.fault_meaning.cite)
        if self.safety_warning:
            out.append(self.safety_warning.cite)
        return out

    @model_validator(mode="after")
    def _every_cite_has_a_source(self) -> "Answer":
        missing = sorted(set(self.cites()) - set(self.sources))
        if missing:
            raise ValueError(f"cites with no entry in sources: {missing}")
        return self


class Nearest(BaseModel):
    chunk_id: str
    doc_id: str
    page: int = Field(ge=1)
    text: str


class Refusal(BaseModel):
    """Below the confidence threshold (AS3.2). Carries no steps of any kind, by construction."""
    kind: Literal["refusal"] = "refusal"
    message: str
    nearest: list[Nearest] = Field(max_length=3)


AskResponse = Annotated[Answer | Refusal, Field(discriminator="kind")]


class Identified(BaseModel):
    model_number: str | None
    fault_code: str | None


class Probe(BaseModel):
    ok: bool
    detail: str


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    qdrant: Probe
    postgres: Probe
