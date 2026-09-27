"""The one place the app calls Claude. Everything else passes a schema and gets a validated object back.

Structured outputs (`messages.parse` + a Pydantic model) guarantee the reply parses
into the schema; they do *not* guarantee a cite is real or a warning is verbatim —
that is generation.generate.finalize's job.
"""
from functools import cache
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from core import config

T = TypeVar("T", bound=BaseModel)


class GenerationError(Exception):
    """The model call failed or returned nothing usable. /ask maps this to 502."""


class GenerationTimeout(GenerationError):
    """The model call ran past GENERATION_TIMEOUT. /ask maps this to 504."""


@cache
def client() -> anthropic.Anthropic:
    # One retry: a phone user waiting on /ask would rather see an error than wait 3x the timeout.
    return anthropic.Anthropic(timeout=config.GENERATION_TIMEOUT, max_retries=1)


def structured(system: str, user: str, schema: type[T], *, max_tokens: int = 8000) -> T:
    """One request, one validated `schema` instance."""
    try:
        response = client().messages.parse(
            model=config.LLM_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=schema,
            output_config={"effort": "low"},  # extraction from given text, not open reasoning
        )
    except anthropic.APITimeoutError as e:
        raise GenerationTimeout(str(e)) from e
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
        raise GenerationError(f"{type(e).__name__}: {e}") from e
    if response.stop_reason in ("refusal", "max_tokens") or response.parsed_output is None:
        raise GenerationError(f"no usable output (stop_reason={response.stop_reason})")
    return response.parsed_output
