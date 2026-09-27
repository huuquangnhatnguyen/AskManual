"""Shared test helpers.

`pending` turns a stub's NotImplementedError into a skip that names the task, so
`pytest` stays green while work is in flight and a test starts running the
moment its stub is filled in. Anything other than NotImplementedError still fails.
"""
from contextlib import contextmanager
from pathlib import Path

import pytest

from core.chunks import load_chunks

FIXTURE_CHUNKS = Path(__file__).parent.parent / "api" / "fixtures" / "chunks.jsonl"


@pytest.fixture
def pending():
    @contextmanager
    def _pending():
        try:
            yield
        except NotImplementedError as e:
            pytest.skip(f"pending: {e}")
    return _pending


@pytest.fixture(scope="session")
def fixture_chunks():
    """The handful of real chunks committed under api/fixtures — enough to exercise retrieval
    and generation plumbing without chunks.jsonl, which isn't in git."""
    return load_chunks(FIXTURE_CHUNKS)
