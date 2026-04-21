from pathlib import Path

import pytest

from bettercast.formats.base import Recording
from bettercast.formats.v2 import V2Parser
from bettercast.formats.v3 import V3Parser

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_recording() -> Recording:
    parser = V2Parser()
    return parser.parse(FIXTURES_DIR / "sample.cast")


@pytest.fixture
def sample_recording_v3() -> Recording:
    parser = V3Parser()
    return parser.parse(FIXTURES_DIR / "sample_v3.cast")
