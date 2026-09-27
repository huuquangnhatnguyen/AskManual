"""AS3.1: the exact fault-code lane."""
from retrieval.codes import CodeRetriever


def test_code_in_question_finds_its_row(fixture_chunks):
    hits = CodeRetriever(fixture_chunks).search("ACS580 is showing fault 2330. What is it?", k=5)
    assert hits and hits[0].page == 553


def test_no_known_code_returns_nothing(fixture_chunks):
    r = CodeRetriever(fixture_chunks)
    assert r.search("how do I wire the motor cable", k=5) == []
    assert r.search("fault 9999", k=5) == []  # a number the corpus never defines as a code


def test_product_family_filter(fixture_chunks):
    assert CodeRetriever(fixture_chunks).search("fault 2330", k=5, product_family="NO_SUCH") == []
