"""api/site.py: the library and results pages read only committed artifacts."""
import json

from api import site


def write(d, name, table):
    (d / f"{name}.json").write_text(json.dumps({"table": table}), encoding="utf-8")


def test_results_reads_hits_over_n_and_marks_the_best(tmp_path):
    write(tmp_path, "baseline", {"fault_code": {"n": 6, "hits": 1}, "OVERALL": {"n": 25, "hits": 9}})
    write(tmp_path, "fused", {"fault_code": {"n": 6, "hits": 6}, "OVERALL": {"n": 25, "hits": 14}})
    r = site.results(tmp_path)
    fused = next(x for x in r["rows"] if x["name"] == "fused")
    assert fused["cells"]["fault_code"] == 1.0 and fused["cells"]["OVERALL"] == 14 / 25
    assert r["best"]["fault_code"] == 1.0 and r["n"]["OVERALL"] == 25
    assert [x["name"] for x in r["rows"]] == ["baseline", "fused"]  # pitch order, missing runs skipped


def test_results_is_none_before_any_run(tmp_path):
    assert site.results(tmp_path) is None


def test_every_catalogued_manual_is_listed():
    ids = [m.doc_id for m in site.manuals()]
    assert ids == [d for d, *_ in site.MANUALS]
