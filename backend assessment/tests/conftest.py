import pytest
from app.repo.candidates import seed


@pytest.fixture(autouse=True)
def reset_store():
    """Re-seed the in-memory store before every test for isolation."""
    seed()
