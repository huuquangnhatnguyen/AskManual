"""AS0.5 contract checks. Run: pytest tests/"""
import io
import json

from fastapi.testclient import TestClient
from PIL import Image
from pydantic import TypeAdapter

from api.main import CHUNKS, app
from api.models import Answer, AskResponse, Refusal

client = TestClient(app)


def test_ask_returns_schema_valid_answer():
    r = client.post("/ask", json={"question": "ACS580 fault 2330?"})
    assert r.status_code == 200
    answer = TypeAdapter(AskResponse).validate_python(r.json())
    assert isinstance(answer, Answer)


def test_every_cite_resolves_to_a_fixture_chunk():
    answer = Answer.model_validate(client.post("/ask", json={"question": "x"}).json())
    assert set(answer.cites()) <= set(CHUNKS)


def test_safety_warning_is_verbatim_in_cited_chunk():
    answer = Answer.model_validate(client.post("/ask", json={"question": "x"}).json())
    assert answer.safety_warning.verbatim in CHUNKS[answer.safety_warning.cite].text


def test_refusal_fixture_has_no_steps():
    r = client.post("/ask?fixture=refusal", json={"question": "Reset a Siemens S7?"})
    refusal = TypeAdapter(AskResponse).validate_python(r.json())
    assert isinstance(refusal, Refusal)
    assert "corrective_steps" not in r.json()


def test_ask_rejects_empty_question():
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_evidence_is_a_png_of_the_bbox():
    r = client.get("/evidence/acs580_firmware_manual_p553_c001")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    img = Image.open(io.BytesIO(r.content))
    # 2330 row: 331.4 x 90.9 pt + 6 pt padding each side, at 150/72 px per pt
    assert abs(img.width - (331.4 + 12) * 150 / 72) <= 2
    assert abs(img.height - (90.9 + 12) * 150 / 72) <= 2


def test_evidence_unknown_or_malformed_is_404():
    assert client.get("/evidence/nope_p1_c000").status_code == 404
    assert client.get("/evidence/..%2F..%2Fetc").status_code == 404
    assert client.get("/evidence/ABC").status_code == 404


def test_identify_accepts_image_rejects_other():
    png = io.BytesIO()
    Image.new("RGB", (4, 4)).save(png, format="PNG")
    r = client.post("/identify", files={"image": ("p.png", png.getvalue(), "image/png")})
    assert r.status_code == 200 and set(r.json()) == {"model_number", "fault_code"}
    r = client.post("/identify", files={"image": ("p.txt", b"hi", "text/plain")})
    assert r.status_code == 415


def test_health_reports_both_backends(monkeypatch, tmp_path):
    from api import config
    monkeypatch.setattr(config, "QDRANT_URL", "")
    monkeypatch.setattr(config, "QDRANT_PATH", tmp_path)  # embedded mode, nothing built
    monkeypatch.setattr(config, "DATABASE_URL", "")
    body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert body["qdrant"]["ok"] is False and body["postgres"]["ok"] is False


def test_health_accepts_a_built_embedded_store(monkeypatch, tmp_path):
    from api import config
    (tmp_path / "collection").mkdir()
    monkeypatch.setattr(config, "QDRANT_URL", "")
    monkeypatch.setattr(config, "QDRANT_PATH", tmp_path)
    assert client.get("/health").json()["qdrant"]["ok"] is True


def test_every_page_renders_with_nav_marking_itself():
    for path, label in [("/", "Ask"), ("/manuals", "Manuals"), ("/results", "Results"), ("/about", "How it works")]:
        r = client.get(path)
        assert r.status_code == 200, path
        assert 'aria-current="page"' in r.text and label in r.text, path


def test_ask_page_hides_the_unshipped_photo_entry():
    # /identify is a canned stub (M5 cut): no UI may invite a real photo into it.
    assert 'type="file"' not in client.get("/").text


def test_answer_page_carries_question_and_stub_knobs():
    r = client.get("/answer", params={"q": "fault 2330?", "family": "ACS580", "fixture": "refusal"})
    assert r.status_code == 200
    assert "fault 2330?" in r.text and '"product_family": "ACS580"' in r.text and "fixture=refusal" in r.text


def test_answer_page_without_question_goes_home():
    r = client.get("/answer", params={"q": "  "}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/"


def test_answer_page_escapes_the_question():
    r = client.get("/answer", params={"q": "</script><script>alert(1)</script>"})
    assert "<script>alert(1)" not in r.text


def test_static_assets_are_served():
    assert client.get("/static/app.css").status_code == 200
    assert client.get("/static/answer.js").status_code == 200


def test_openapi_documents_all_four_routes():
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/ask", "/identify", "/evidence/{chunk_id}", "/health"} <= set(paths)
    json.dumps(paths)  # serialisable
