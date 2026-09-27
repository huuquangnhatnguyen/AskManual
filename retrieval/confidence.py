"""AS3.2 — the refusal gate: one tunable threshold on the fused top score.

Calibrate with `python -m eval.calibrate`: every eval/data/out_of_corpus.jsonl
question must land below the threshold and every gold question above it.
The chosen value goes in REFUSAL_THRESHOLD (.env, read by core/config.py).
"""
from core import config
from retrieval.base import Hit


def top_score(hits: list[Hit]) -> float:
    return hits[0].score if hits else 0.0


def should_refuse(hits: list[Hit], threshold: float | None = None) -> bool:
    t = config.REFUSAL_THRESHOLD if threshold is None else threshold
    return top_score(hits) < t
