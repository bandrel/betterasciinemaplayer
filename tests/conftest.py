from pathlib import Path

import pytest

from bettercast.formats.base import Recording
from bettercast.formats.v2 import V2Parser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_recording() -> Recording:
    parser = V2Parser()
    return parser.parse(FIXTURES_DIR / "sample.cast")
