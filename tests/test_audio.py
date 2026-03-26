import wave
from pathlib import Path

import pytest

from asr_client.audio_processing import AudioFile, AudioFileStream


@pytest.fixture
def nonsilent_wav_path(tmp_path: Path) -> Path:
    """Generate a mono 16-bit PCM WAV file with non-zero content for distinguishing silence from audio."""
    path = tmp_path / "nonsilent.wav"
    sample_rate = 16000
    num_frames = sample_rate  # 1 second
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x01\x00" * num_frames)
    return path


def test_audio_file_loads(wav_path: Path) -> None:
    audio = AudioFile(wav_path)
    assert audio.sampling_rate_hz > 0
    assert len(audio.data) > 0
    assert audio.bit_depth == 16


def test_audio_file_stream_iterates(wav_path: Path) -> None:
    stream = AudioFileStream(wav_path)
    chunks = list(stream)
    assert len(chunks) > 0
    assert all(isinstance(c, bytes) for c in chunks)


def test_audio_file_stream_closed_after_exhaust(wav_path: Path) -> None:
    stream = AudioFileStream(wav_path)
    list(stream)
    assert stream.closed


def test_audio_file_invalid_path() -> None:
    with pytest.raises(FileNotFoundError):
        AudioFile(Path("/nonexistent/file.wav"))


def test_audio_file_stream_prepends_silence(wav_path: Path) -> None:
    prepend_ms = 150
    sample_rate = 16000
    bit_depth = 16
    silence_byte_count = int(prepend_ms / 1000 * sample_rate) * (bit_depth // 8)
    original_byte_count = len(AudioFile(wav_path).data)

    stream = AudioFileStream(wav_path, prepend_silence_ms=prepend_ms)
    total = b"".join(stream)

    assert len(total) == silence_byte_count + original_byte_count
    assert total[:silence_byte_count] == bytes(silence_byte_count)


def test_audio_file_stream_prepend_silence_chunked(nonsilent_wav_path: Path) -> None:
    prepend_ms = 150
    chunk_ms = 50
    sample_rate = 16000
    bit_depth = 16
    silence_byte_count = int(prepend_ms / 1000 * sample_rate) * (bit_depth // 8)
    chunk_byte_count = int(chunk_ms / 1000 * sample_rate) * (bit_depth // 8)
    silence_chunks = silence_byte_count // chunk_byte_count

    stream = AudioFileStream(nonsilent_wav_path, chunk_duration_ms=chunk_ms, prepend_silence_ms=prepend_ms)
    chunks = list(stream)

    # The first silence_chunks chunks must be entirely zero bytes.
    for i in range(silence_chunks):
        assert chunks[i] == bytes(chunk_byte_count), f"chunk {i} should be silence"
    # The chunk immediately after silence must contain non-zero audio bytes.
    assert any(b != 0 for b in chunks[silence_chunks])


def test_audio_file_stream_prepend_silence_zero(wav_path: Path) -> None:
    original_byte_count = len(AudioFile(wav_path).data)
    stream = AudioFileStream(wav_path, prepend_silence_ms=0)
    total = b"".join(stream)
    assert len(total) == original_byte_count


def test_audio_file_stream_appends_silence(nonsilent_wav_path: Path) -> None:
    append_ms = 150
    sample_rate = 16000
    bit_depth = 16
    silence_byte_count = int(append_ms / 1000 * sample_rate) * (bit_depth // 8)
    original_byte_count = len(AudioFile(nonsilent_wav_path).data)

    stream = AudioFileStream(nonsilent_wav_path, append_silence_ms=append_ms)
    total = b"".join(stream)

    assert len(total) == original_byte_count + silence_byte_count
    assert total[-silence_byte_count:] == bytes(silence_byte_count)
    # The last audio sample (2 bytes) before the silence must contain non-zero data.
    assert any(b != 0 for b in total[-silence_byte_count - 2 : -silence_byte_count])


def test_audio_file_stream_append_silence_chunked(nonsilent_wav_path: Path) -> None:
    append_ms = 150
    chunk_ms = 50
    sample_rate = 16000
    bit_depth = 16
    silence_byte_count = int(append_ms / 1000 * sample_rate) * (bit_depth // 8)
    chunk_byte_count = int(chunk_ms / 1000 * sample_rate) * (bit_depth // 8)
    silence_chunks = silence_byte_count // chunk_byte_count

    stream = AudioFileStream(nonsilent_wav_path, chunk_duration_ms=chunk_ms, append_silence_ms=append_ms)
    chunks = list(stream)

    # The last silence_chunks chunks must be entirely zero bytes.
    for i in range(len(chunks) - silence_chunks, len(chunks)):
        assert chunks[i] == bytes(chunk_byte_count), f"chunk {i} should be silence"
    # The chunk immediately before silence must contain non-zero audio bytes.
    assert any(b != 0 for b in chunks[len(chunks) - silence_chunks - 1])


def test_audio_file_stream_append_silence_zero(wav_path: Path) -> None:
    original_byte_count = len(AudioFile(wav_path).data)
    stream = AudioFileStream(wav_path, append_silence_ms=0)
    total = b"".join(stream)
    assert len(total) == original_byte_count


def test_audio_file_stream_prepend_and_append_silence(nonsilent_wav_path: Path) -> None:
    prepend_ms = 150
    append_ms = 300
    sample_rate = 16000
    bit_depth = 16
    prepend_bytes = int(prepend_ms / 1000 * sample_rate) * (bit_depth // 8)
    append_bytes = int(append_ms / 1000 * sample_rate) * (bit_depth // 8)
    original_byte_count = len(AudioFile(nonsilent_wav_path).data)

    stream = AudioFileStream(nonsilent_wav_path, prepend_silence_ms=prepend_ms, append_silence_ms=append_ms)
    total = b"".join(stream)

    assert len(total) == prepend_bytes + original_byte_count + append_bytes
    assert total[:prepend_bytes] == bytes(prepend_bytes)
    assert total[-append_bytes:] == bytes(append_bytes)
    # First audio sample after leading silence must be non-zero.
    assert any(b != 0 for b in total[prepend_bytes : prepend_bytes + 2])
    # Last audio sample before trailing silence must be non-zero.
    assert any(b != 0 for b in total[-append_bytes - 2 : -append_bytes])
