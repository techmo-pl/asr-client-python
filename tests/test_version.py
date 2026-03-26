import re

from asr_client.VERSION import __version__


def test_version_format() -> None:
    assert re.match(r"^\d+\.\d+\.\d+$", __version__)
