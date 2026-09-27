"""The second refusal gate: generate() refuses when the model says the excerpts don't answer,
or when nothing it cited survives finalize. No model call; the Draft is canned."""
from api.models import Answer, Refusal
from generation import generate as gen
from generation.generate import DCited, DStep, Draft

ROW = "acs580_firmware_manual_p553_c001"


def empty(**over) -> Draft:
    return Draft(**{**dict(fault_meaning=None, probable_causes=[], corrective_steps=[],
                           tools_and_parts=[], safety_warning=None), **over})


def run(monkeypatch, fixture_chunks, d: Draft):
    monkeypatch.setattr(gen.llm, "structured", lambda *a, **k: d)
    return gen.generate("q", [fixture_chunks[ROW]])


def test_model_says_unanswerable(monkeypatch, fixture_chunks):
    d = empty(answerable=False, fault_meaning=DCited(text="Earth leakage", cite=ROW))
    r = run(monkeypatch, fixture_chunks, d)
    assert isinstance(r, Refusal) and r.nearest[0].chunk_id == ROW


def test_every_cite_invented_refuses(monkeypatch, fixture_chunks):
    d = empty(corrective_steps=[DStep(n=1, text="Reset the PLC", cite="siemens_s7_manual_p1_c000")])
    assert isinstance(run(monkeypatch, fixture_chunks, d), Refusal)


def test_grounded_draft_answers(monkeypatch, fixture_chunks):
    d = empty(fault_meaning=DCited(text="Earth leakage", cite=ROW))
    a = run(monkeypatch, fixture_chunks, d)
    assert isinstance(a, Answer) and set(a.sources) == {ROW}
