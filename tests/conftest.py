import wave
from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--asr-service-address",
        default=None,
        help="host:port of a live ASR service (enables integration tests)",
    )


@pytest.fixture
def wav_path(tmp_path: Path) -> Path:
    """Generate a minimal valid mono 16-bit PCM WAV file for testing."""
    path = tmp_path / "test.wav"
    sample_rate = 16000
    num_frames = sample_rate  # 1 second of silence
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return path
