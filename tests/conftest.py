import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir(monkeypatch):
    """Put the fixtures directory on sys.path so they can be imported by name."""
    monkeypatch.syspath_prepend(str(FIXTURES))
    yield FIXTURES
    for name in ("clean_module", "broken_module"):
        sys.modules.pop(name, None)
