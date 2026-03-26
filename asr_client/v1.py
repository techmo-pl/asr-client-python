from __future__ import annotations

import time
from collections.abc import Iterator
from itertools import chain

import grpc
from asr_api import v1, v1p1
from asr_api import v1p1 as api

from asr_client import _generate_request_with_traceback
from asr_client.audio_processing import AudioStream


@_generate_request_with_traceback
def _generate_streaming_recognize_request_with_config(
    audio_encoding: int | str,
    audio_sampling_rate_hz: float,
    enable_age_recognition: bool = True,
    enable_auto_hold_response: bool = False,
    enable_gender_recognition: bool = True,
    enable_held_responses_merging: bool = False,
    enable_interim_results: bool = False,
    enable_language_recognition: bool = True,
    enable_manual_input_timer: bool = False,
    enable_single_utterance: bool = True,
    enable_speech_recognition_time_alignment: bool = False,
    speech_recognition_alternatives_limit: int = 1,
    speech_recognition_language_group_name: str | None = None,
    speech_recognition_model_name: str | None = None,
    timeouts: dict[str, int] | None = None,
    additional_config_specs: dict[str, str] | None = None,
) -> Iterator[api.StreamingRecognizeRequest]:

    yield api.StreamingRecognizeRequest(
        config=api.StreamingRecognizeRequestConfig(
            audio_config=api.AudioConfig(
                encoding=audio_encoding,
                sampling_rate_hz=audio_sampling_rate_hz,
            ),
            result_config=api.ResultConfig(
                enable_single_utterance=enable_single_utterance,
                enable_interim_results=enable_interim_results,
                enable_held_responses_merging=enable_held_responses_merging,
            ),
            streaming_config=api.StreamingConfig(
                enable_auto_hold_response=enable_auto_hold_response or enable_held_responses_merging,
                enable_manual_input_timer=enable_manual_input_timer,
            ),
            speech_recognition_config=api.SpeechRecognitionConfig(
                enable_speech_recognition=True,  # TODO
                recognition_alternatives_limit=speech_recognition_alternatives_limit,
                enable_time_alignment=enable_speech_recognition_time_alignment,
                language_group_name=speech_recognition_language_group_name,
                model_name=speech_recognition_model_name,
                config_fields=(
                    ([] if timeouts is None else [(key, str(value)) for (key, value) in timeouts.items()])
                    + ([] if additional_config_specs is None else [(key, str(value)) for (key, value) in additional_config_specs.items()])
                ),
            ),
            age_recognition_config=api.AgeRecognitionConfig(
                enable_age_recognition=enable_age_recognition,
            ),
            gender_recognition_config=api.GenderRecognitionConfig(
                enable_gender_recognition=enable_gender_recognition,
            ),
            language_recognition_config=api.LanguageRecognitionConfig(
                enable_language_recognition=enable_language_recognition,
            ),
        )
    )


@_generate_request_with_traceback
def _generate_streaming_recognize_request_with_control_message(
    start_input_timer: bool | None = None,
) -> Iterator[api.StreamingRecognizeRequest]:
    yield api.StreamingRecognizeRequest(
        control_message=api.StreamingRecognizeRequestControlMessage(
            start_input_timer=start_input_timer,
        )
    )


@_generate_request_with_traceback
def _generate_streaming_recognize_request_with_data_or_control_message(
    audio_stream: AudioStream,
    audio_stream_interval_ms: int = 0,
    start_input_timer_control_message_interspace: int | None = None,
) -> Iterator[api.StreamingRecognizeRequest]:
    audio_stream_interval_s = audio_stream_interval_ms / 1000

    for audio_stream_chunk_count, audio_chunk in enumerate(audio_stream, start=1):
        time.sleep(audio_stream_interval_s)

        yield api.StreamingRecognizeRequest(
            data=api.StreamingRecognizeRequestData(
                audio=api.Audio(bytes=audio_chunk),
            )
        )

        if start_input_timer_control_message_interspace != 0:
            if audio_stream_chunk_count % start_input_timer_control_message_interspace == 0:
                yield from _generate_streaming_recognize_request_with_control_message(start_input_timer=True)


class Asr:
    def __init__(self, grpc_channel: grpc.Channel, api_patch_version: int | None = None):
        if api_patch_version is None:
            self._grpc_stub = v1.AsrStub(grpc_channel)
        elif api_patch_version == 1:
            self._grpc_stub = v1p1.AsrStub(grpc_channel)
        else:
            raise ValueError(f"unsupported API patch version: {api_patch_version}")

    def streaming_recognize(
        self,
        audio_stream: AudioStream,
        audio_stream_interval_ms: int = 0,
        enable_manual_input_timer: bool = False,
        grpc_timeout_ms: int | None = None,
        session_id: str | None = None,
        start_input_timer_control_message_interspace: int | None = 0,
        **kwargs,
    ) -> grpc.Call:
        return self._grpc_stub.StreamingRecognize(
            chain(
                _generate_streaming_recognize_request_with_config(
                    audio_encoding=api.AudioConfig.AudioEncoding.LINEAR16,  # TODO: audio_stream.audio_encoding
                    audio_sampling_rate_hz=audio_stream.sampling_rate_hz,
                    enable_manual_input_timer=enable_manual_input_timer,
                    **kwargs,
                ),
                _generate_streaming_recognize_request_with_data_or_control_message(
                    audio_stream=audio_stream,
                    audio_stream_interval_ms=audio_stream_interval_ms,
                    start_input_timer_control_message_interspace=start_input_timer_control_message_interspace,
                ),
            ),
            metadata=(("session-id", session_id),) if session_id else None,
            timeout=grpc_timeout_ms / 1000 if grpc_timeout_ms is not None else None,
        )
