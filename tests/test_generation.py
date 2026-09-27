"""AS4.1 / AS4.2 / AS4.3 — generation guards and the /ask pipeline, with no model call.

The model is replaced by a canned Draft; what's under test is what we do with it.
"""
import pytest

from api.models import Answer, Refusal
from generation import generate as gen
from generation.generate import DCause, DCited, Draft, DStep, DWarning, finalize
from generation.prompt import format_context
from generation.refusal import refuse

ROW = "acs580_firmware_manual_p553_c001"   # the 2330 table row
SAFE = "acs580_firmware_manual_p535_c004"  # the WARNING! prose chunk


@pytest.fixture
def chunks(fixture_chunks):
    return [fixture_chunks[ROW], fixture_chunks[SAFE]]


def draft(fixture_chunks, **over) -> Draft:
    base = dict(
        fault_meaning=DCited(text="Earth leakage", cite=ROW),
        probable_causes=[DCause(text="Earth fault in motor cable", likelihood="high", cite=ROW)],
        corrective_steps=[DStep(n=1, text="Check for capacitors", cite=ROW),
                          DStep(n=2, text="Measure insulation", cite=ROW)],
        tools_and_parts=[],
        safety_warning=DWarning(verbatim=fixture_chunks[SAFE].text[:60], cite=SAFE),
    )
    return Draft(**{**base, **over})


def test_context_tags_each_excerpt_with_its_id(chunks):
    ctx = format_context(chunks)
    assert f'id="{ROW}"' in ctx and f'id="{SAFE}"' in ctx and "Fault messages" in ctx


def test_finalize_builds_sources_from_surviving_cites(pending, fixture_chunks, chunks):
    with pending():
        a = finalize(draft(fixture_chunks), chunks)
    assert isinstance(a, Answer)
    assert set(a.sources) == {ROW, SAFE}
    assert a.sources[ROW].page == 553


def test_safety_warning_is_verbatim_in_cited_chunk(pending, fixture_chunks, chunks):
    with pending():
        a = finalize(draft(fixture_chunks), chunks)
    assert a.safety_warning.verbatim in fixture_chunks[a.safety_warning.cite].text


def test_paraphrased_safety_warning_is_dropped(pending, fixture_chunks, chunks):
    d = draft(fixture_chunks, safety_warning=DWarning(verbatim="Be careful near the drive.", cite=SAFE))
    with pending():
        assert finalize(d, chunks).safety_warning is None


def test_items_citing_unseen_chunks_are_dropped_and_steps_renumbered(pending, fixture_chunks, chunks):
    d = draft(fixture_chunks, corrective_steps=[
        DStep(n=1, text="Invented step", cite="acs880_primary_firmware_manual_p1_c000"),
        DStep(n=2, text="Measure insulation", cite=ROW)])
    with pending():
        a = finalize(d, chunks)
    assert [(s.n, s.text) for s in a.corrective_steps] == [(1, "Measure insulation")]
    assert "acs880_primary_firmware_manual_p1_c000" not in a.sources


def test_refusal_carries_three_nearest_and_no_steps(pending, fixture_chunks):
    with pending():
        r = refuse(list(fixture_chunks.values()) * 2)
    assert isinstance(r, Refusal) and len(r.nearest) <= 3
    assert "corrective_steps" not in r.model_dump()


def test_pipeline_generates_above_threshold(pending, monkeypatch, fixture_chunks):
    from api import pipeline
    from retrieval.keyword import KeywordRetriever
    monkeypatch.setattr(pipeline, "chunk_store", lambda: fixture_chunks)
    monkeypatch.setattr(gen.llm, "structured", lambda *a, **k: draft(fixture_chunks))
    monkeypatch.setattr(pipeline, "should_refuse", lambda hits: False)
    with pending():
        resp = pipeline.answer_question("fault 2330 earth leakage", retriever=KeywordRetriever(fixture_chunks))
    assert isinstance(resp, Answer)


def test_pipeline_refuses_below_threshold(pending, monkeypatch, fixture_chunks):
    from api import pipeline
    from retrieval.keyword import KeywordRetriever
    monkeypatch.setattr(pipeline, "chunk_store", lambda: fixture_chunks)
    monkeypatch.setattr(pipeline, "should_refuse", lambda hits: True)
    with pending():
        resp = pipeline.answer_question("reset a Siemens S7", retriever=KeywordRetriever(fixture_chunks))
    assert isinstance(resp, Refusal)
