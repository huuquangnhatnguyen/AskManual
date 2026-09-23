"""The chunk contract from schema.md, as a check. schema.md is the source of truth."""
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

FAULT_CODE = re.compile(r"^[0-9A-F]{4}$")


class Chunk(BaseModel):
    chunk_id: str = Field(pattern=r"^[a-z0-9_]+$")
    doc_id: str
    product_family: list[str] = Field(min_length=1)
    page: int = Field(ge=1)
    bbox: tuple[float, float, float, float]
    chunk_type: Literal["prose", "table_row", "figure", "heading"]
    text: str = Field(min_length=1)
    parent_section_id: str | None
    parent_section_title: str | None
    fault_codes: list[str]
    source_image: str

    @field_validator("product_family")
    @classmethod
    def _uppercase_families(cls, v: list[str]) -> list[str]:
        if any(f != f.upper() for f in v):
            raise ValueError("product_family entries must be uppercase")
        return v

    @field_validator("fault_codes")
    @classmethod
    def _fault_code_format(cls, v: list[str]) -> list[str]:
        bad = [c for c in v if not FAULT_CODE.match(c)]
        if bad:
            raise ValueError(f"fault codes must be 4 uppercase hex chars: {bad}")
        return v

    @model_validator(mode="after")
    def _invariants(self) -> "Chunk":
        if not self.chunk_id.startswith(f"{self.doc_id}_p{self.page}_c"):
            raise ValueError("chunk_id must start with {doc_id}_p{page}_c")
        x0, y0, x1, y1 = self.bbox
        if not (0 <= x0 < x1 and 0 <= y0 < y1):
            raise ValueError("bbox must be [x0, y0, x1, y1] with x0<x1, y0<y1, non-negative")
        if self.chunk_type == "table_row" and " | " not in self.text:
            raise ValueError("table_row text must join cells with ' | '")
        return self

    def check_page_bounds(self, width: float, height: float) -> None:
        """The upper-bound invariant needs the page size, which the chunk doesn't carry."""
        x0, y0, x1, y1 = self.bbox
        if x1 > width or y1 > height:
            raise ValueError(f"{self.chunk_id}: bbox {self.bbox} exceeds page {width}x{height}")
