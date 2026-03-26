from __future__ import annotations

import math
import queue
import warnings
from pathlib import Path

import pyaudio

with warnings.catch_warnings():
    warnings.simplefilter("ignore", SyntaxWarning)
    import pydub
    import pydub.exceptions


class AudioFileError(RuntimeError):
    def __init__(self, audio_file_path: Path, message: str):
        super().__init__(f"{audio_file_path}: {message}: only mono, 16 bit PCM audio files are allowed")


class AudioFile:
    def __init__(self, path: Path):
        try:
            self._audio_segment = pydub.AudioSegment.from_wav(path)
        except pydub.exceptions.CouldntDecodeError:
            raise AudioFileError(path, "has unknown or unsupported format") from None

        if self._audio_segment.channels != 1:
            raise AudioFileError(path, f"has {self._audio_segment.channels} channels")

        self._bit_depth = self._audio_segment.sample_width * 8

        if self._bit_depth != 16:
            raise AudioFileError(path, f"has {self._bit_depth} bit depth")

    @property
    def bit_depth(self) -> int:
        return self._bit_depth

    @property
    def data(self) -> bytes:
        return self._audio_segment.raw_data

    @property
    def sampling_rate_hz(self) -> float:
        return self._audio_segment.frame_rate


class Audio:
    def __init__(self, sampling_rate_hz: float):
        self._sampling_rate_hz = float(sampling_rate_hz)

    @property
    def sampling_rate_hz(self) -> float:
        return self._sampling_rate_hz


class AudioStream(Audio):
    def __init__(self, sampling_rate_hz: float):
        super().__init__(sampling_rate_hz)
        self._closed = False

    def close(self):
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed


class AudioFileStream(AudioStream):
    def __init__(
        self,
        audio_file_path: Path,
        chunk_duration_ms: int | None = None,
        sampling_rate_hz: None | int = None,
        prepend_silence_ms: int = 0,
        append_silence_ms: int = 0,
    ):
        self._audio_file = AudioFile(audio_file_path)

        effective_sampling_rate_hz = sampling_rate_hz if sampling_rate_hz is not None else self._audio_file.sampling_rate_hz
        super().__init__(sampling_rate_hz=effective_sampling_rate_hz)

        # Compute silence in whole samples first to guarantee PCM byte alignment.
        sample_width_bytes = self._audio_file.bit_depth // 8

        self._data = self._audio_file.data

        if prepend_silence_ms > 0:
            self._data = bytes(int(prepend_silence_ms / 1000 * self.sampling_rate_hz) * sample_width_bytes) + self._data

        if append_silence_ms > 0:
            self._data = self._data + bytes(int(append_silence_ms / 1000 * self.sampling_rate_hz) * sample_width_bytes)

        self._audio_data_slice_size = (
            int(chunk_duration_ms / 1000 * self.sampling_rate_hz * self._audio_file.bit_depth / 8) if chunk_duration_ms is not None else len(self._data)
        )

    def __iter__(self):
        self._audio_data_slice_begin = 0
        self._closed = False
        return self

    def __next__(self):
        if self.closed:
            raise StopIteration

        audio_data_slice_end = self._audio_data_slice_begin + self._audio_data_slice_size

        if audio_data_slice_end >= len(self._data):
            audio_data_slice_end = len(self._data)
            self.close()

        audio_data_slice = self._data[self._audio_data_slice_begin : audio_data_slice_end]

        self._audio_data_slice_begin = audio_data_slice_end

        return audio_data_slice


class MicrophoneStream(AudioStream):
    def __init__(self, sampling_rate_hz: int = 16000, chunk_duration_ms: int = 200, prepend_silence_ms: int = 0, append_silence_ms: int = 0):
        super().__init__(sampling_rate_hz=sampling_rate_hz)

        self._audio_buffer = queue.Queue()
        self._audio_buffer_chunk_size = int(chunk_duration_ms / 1000 * self.sampling_rate_hz)
        # 16-bit PCM: 2 bytes per sample. Silence chunk matches PyAudio buffer size exactly.
        # Reused for both prepend and append silence.
        self._silence_chunk = bytes(self._audio_buffer_chunk_size * 2)
        # ceil guarantees at least the requested silence duration (may overshoot by < chunk_duration_ms).
        # Note: the PyAudio stream opens in __iter__ and starts recording immediately, so audio
        # accumulates in the buffer while prepend silence chunks are being yielded.
        self._prepend_silence_chunks = math.ceil(prepend_silence_ms / chunk_duration_ms) if prepend_silence_ms > 0 else 0
        self._silence_chunks_remaining = 0
        # Append silence is yielded after close() is called, before StopIteration.
        self._append_silence_chunks = math.ceil(append_silence_ms / chunk_duration_ms) if append_silence_ms > 0 else 0
        self._append_silence_chunks_remaining = 0
        self._audio_interface = pyaudio.PyAudio()

    def __del__(self):
        if hasattr(self, "_audio_interface"):
            self._audio_interface.terminate()

    def _fill_audio_buffer(self, data, _, __, ___) -> tuple[bytes | None, int]:
        self._audio_buffer.put(data)
        return None, pyaudio.paContinue

    def __iter__(self):
        self._audio_stream = self._audio_interface.open(
            channels=1,
            input=True,
            format=pyaudio.paInt16,
            frames_per_buffer=self._audio_buffer_chunk_size,
            rate=int(self.sampling_rate_hz),
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer does not
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_audio_buffer,
        )
        self._closed = False
        self._silence_chunks_remaining = self._prepend_silence_chunks
        self._append_silence_chunks_remaining = self._append_silence_chunks

        return self

    def __next__(self) -> bytes:
        if self.closed:
            if self._append_silence_chunks_remaining > 0:
                self._append_silence_chunks_remaining -= 1
                return self._silence_chunk
            self._audio_stream.stop_stream()
            self._audio_stream.close()
            raise StopIteration

        if self._silence_chunks_remaining > 0:
            self._silence_chunks_remaining -= 1
            return self._silence_chunk

        return self._audio_buffer.get()
