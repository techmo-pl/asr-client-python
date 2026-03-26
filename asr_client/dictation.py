from __future__ import annotations

import time
from collections.abc import Iterator
from itertools import chain

import grpc
from asr_api import dictation as api

from asr_client import _generate_request_with_traceback
from asr_client.audio_processing import AudioStream


@_generate_request_with_traceback
def _generate_streaming_recognize_request_with_config(
    audio_encoding: int | str,
    audio_sampling_rate_hz: float,
    enable_age_recognition: bool = True,
    enable_gender_recognition: bool = True,
    enable_interim_results: bool = False,
    enable_single_utterance: bool = True,
    enable_speech_recognition_time_alignment: bool = False,
    speech_recognition_alternatives_limit: int = 1,
    speech_recognition_language_group_name: str | None = None,
    speech_recognition_model_name: str | None = None,
    timeouts: dict[str, int] | None = None,
    additional_config_specs: dict[str, str] | None = None,
    **kwargs,
) -> Iterator[api.StreamingRecognizeRequest]:
    if audio_sampling_rate_hz.is_integer():
        audio_sampling_rate_hz = int(audio_sampling_rate_hz)

    yield api.StreamingRecognizeRequest(
        streaming_config=api.StreamingRecognitionConfig(
            config=api.RecognitionConfig(
                config_fields=(
                    ([] if timeouts is None else [api.ConfigField(key=key, value=str(value)) for (key, value) in timeouts.items()])
                    + (
                        [
                            api.ConfigField(key="recognize-age", value="true"),
                        ]
                        if enable_age_recognition
                        else []
                    )
                    + (
                        [
                            api.ConfigField(key="recognize-gender", value="true"),
                        ]
                        if enable_gender_recognition
                        else []
                    )
                    + (
                        []
                        if additional_config_specs is None
                        else [api.ConfigField(key=key, value=str(value)) for key, value in additional_config_specs.items()]
                    )
                ),
                enable_word_time_offsets=enable_speech_recognition_time_alignment,
                encoding=audio_encoding,
                language_code=speech_recognition_language_group_name,
                max_alternatives=speech_recognition_alternatives_limit,
                sample_rate_hertz=audio_sampling_rate_hz,
                speech_contexts=([api.SpeechContext(phrases=[speech_recognition_model_name])] if speech_recognition_model_name is not None else None),
            ),
            interim_results=enable_interim_results,
            single_utterance=enable_single_utterance,
        )
    )


@_generate_request_with_traceback
def _generate_streaming_recognize_request_with_data(audio_stream: AudioStream, audio_stream_interval_ms: int = 0) -> Iterator[api.StreamingRecognizeRequest]:
    audio_stream_interval_s = audio_stream_interval_ms / 1000

    for audio_chunk in audio_stream:
        time.sleep(audio_stream_interval_s)

        yield api.StreamingRecognizeRequest(audio_content=audio_chunk)


class Asr:
    def __init__(self, grpc_channel: grpc.Channel):
        self._grpc_stub = api.SpeechStub(grpc_channel)

    def streaming_recognize(
        self,
        audio_stream: AudioStream,
        audio_stream_interval_ms: int = 0,
        grpc_timeout_ms: int | None = None,
        session_id: str | None = None,
        **kwargs,
    ) -> grpc.Call:
        return self._grpc_stub.StreamingRecognize(
            chain(
                _generate_streaming_recognize_request_with_config(
                    audio_encoding=api.RecognitionConfig.AudioEncoding.LINEAR16,  # TODO: audio_stream.audio_encoding
                    audio_sampling_rate_hz=audio_stream.sampling_rate_hz,
                    **kwargs,
                ),
                _generate_streaming_recognize_request_with_data(
                    audio_stream=audio_stream,
                    audio_stream_interval_ms=audio_stream_interval_ms,
                ),
            ),
            metadata=(("session_id", session_id),) if session_id else None,
            timeout=grpc_timeout_ms / 1000 if grpc_timeout_ms is not None else None,
        )
