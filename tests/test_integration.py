"""Integration tests: run the CLI against a live ASR service.

These tests are skipped unless ``--asr-service-address`` is supplied, so
the test suite stays fully self-contained in CI unit-test jobs and in local
runs without a server.

Example (local)::

    pytest tests/test_integration.py --asr-service-address dragon:31796
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest


def _parse_all_json_objects(text: str) -> List[object]:
    """Extract every JSON object from *text*, preserving all of them.

    The CLI prints header lines followed by one JSON block per streamed
    response.  ``json.loads`` would fail on multiple objects, so we use
    ``JSONDecoder.raw_decode`` to consume them one at a time.
    """
    decoder = json.JSONDecoder()
    objects = []
    idx = text.find("{")
    while idx != -1:
        obj, end = decoder.raw_decode(text, idx)
        objects.append(obj)
        next_brace = text.find("{", end)
        idx = next_brace
    return objects


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def asr_service_address(request: pytest.FixtureRequest) -> str:
    address = request.config.getoption("--asr-service-address")
    if not address:
        pytest.skip("no --asr-service-address provided")
    assert isinstance(address, str)
    return address


@pytest.fixture
def audio_wav() -> Path:
    """Return the bundled audio.wav from data/."""
    path = Path(__file__).parent.parent / "data" / "audio.wav"
    if not path.exists():
        pytest.skip("data/audio.wav not found")
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


_TIMEOUT_S = 60


def test_cli_recognition_v1p1(asr_service_address: str, audio_wav: Path) -> None:
    """CLI recognises audio.wav via v1p1 API; all responses contain 'result'."""
    result = subprocess.run(
        [sys.executable, "-m", "asr_client", "-s", asr_service_address, "-a", str(audio_wav), "--api-version", "v1p1"],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
    )
    assert result.returncode == 0, f"exit {result.returncode}:\n{result.stderr}"
    responses = _parse_all_json_objects(result.stdout)
    assert responses, f"No JSON found in output:\n{result.stdout}"
    for resp in responses:
        assert isinstance(resp, dict) and "result" in resp, f"'result' key missing from response:\n{resp}"


def test_cli_recognition_v1(asr_service_address: str, audio_wav: Path) -> None:
    """CLI recognises audio.wav via v1 API; all responses contain 'result'."""
    result = subprocess.run(
        [sys.executable, "-m", "asr_client", "-s", asr_service_address, "-a", str(audio_wav), "--api-version", "v1"],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
    )
    assert result.returncode == 0, f"exit {result.returncode}:\n{result.stderr}"
    responses = _parse_all_json_objects(result.stdout)
    assert responses, f"No JSON found in output:\n{result.stdout}"
    for resp in responses:
        assert isinstance(resp, dict) and "result" in resp, f"'result' key missing from response:\n{resp}"


def test_cli_recognition_dictation(asr_service_address: str, audio_wav: Path) -> None:
    """CLI recognises audio.wav via legacy dictation API; all responses contain 'results'."""
    result = subprocess.run(
        [sys.executable, "-m", "asr_client", "-s", asr_service_address, "-a", str(audio_wav), "--api-version", "dictation"],
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_S,
    )
    assert result.returncode == 0, f"exit {result.returncode}:\n{result.stderr}"
    responses = _parse_all_json_objects(result.stdout)
    assert responses, f"No JSON found in output:\n{result.stdout}"
    for resp in responses:
        assert isinstance(resp, dict) and "results" in resp, f"'results' key missing from dictation response:\n{resp}"
