"""Product family inferred from the question text."""
from retrieval.scope import infer_family, named_families

KNOWN = frozenset({"ACS580", "ACS880", "ACQ580"})


def test_one_named_family_scopes():
    assert infer_family("torque for the PE lug on an ACS580-01 frame R1?", KNOWN) == "ACS580"
    assert infer_family("relay outputs on an acs 880 control unit", KNOWN) == "ACS880"


def test_two_families_is_cross_manual_and_does_not_scope():
    assert named_families("swapping an ACS550 R6 for an ACS580") == {"ACS550", "ACS580"}
    assert infer_family("swapping an ACS550 R6 for an ACS580", KNOWN) is None


def test_unknown_or_absent_family_does_not_scope():
    assert infer_family("how do I reset an ACS550?", KNOWN) is None  # not in the corpus: don't empty the results
    assert infer_family("what does fault 2330 mean", KNOWN) is None
