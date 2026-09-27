"""What sits behind POST /ask when PIPELINE=real (AS4.3): retrieve -> gate -> generate or refuse.

This file is orchestration only. Each step lives in its own package and is swapped
there; nothing here should grow logic of its own.
"""
from api.models import Answer, Refusal
from core.chunks import chunk_store
from generation.generate import generate
from generation.refusal import refuse
from retrieval import registry
from retrieval.base import Retriever
from retrieval.confidence import should_refuse

TOP_K = 8  # chunks handed to generation; recall is measured at 5, generation gets a little slack


def answer_question(question: str, product_family: str | None = None,
                    retriever: Retriever | None = None) -> Answer | Refusal:
    from core import config
    retriever = retriever or registry.get(config.RETRIEVER)
    hits = retriever.search(question, k=TOP_K, product_family=product_family)
    store = chunk_store()
    chunks = [store[h.chunk_id] for h in hits if h.chunk_id in store]
    if should_refuse(hits) or not chunks:
        return refuse(chunks)
    return generate(question, chunks)
