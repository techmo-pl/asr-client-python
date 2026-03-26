#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import signal
import textwrap
from pathlib import Path

import grpc
from google.protobuf import json_format

from asr_client import (
    VERSION,
    audio_processing,
    create_grpc_channel,
    create_grpc_channel_credentials,
    dictation,
    v1,
)

legal_header = textwrap.dedent(
    f"""
    Techmo ASR Client, version {VERSION.__version__}
    """
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        allow_abbrev=False,
        description=legal_header,
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--help",
        "-h",
        action="help",
        help="show this help message and exit",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=VERSION.__version__,
        help="show program's version number and exit",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="hides additional output",
    )

    class Once(argparse.Action):
        def __call__(self, parser, namespace, values, _=None):
            if getattr(namespace, self.dest, self.default) is not self.default:
                parser.error("argument {}: allowed once".format("/".join(self.option_strings)))
            setattr(namespace, self.dest, values)

    def assure_int(value: str) -> int:
        try:
            result = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid int value: '{value}'") from None
        else:
            return result

    def non_empty_str(value: str) -> str:
        if not value:
            raise argparse.ArgumentTypeError("must not be empty if set")

        return value

    def positive_int(value: str) -> int:
        if (n := assure_int(value)) <= 0:
            raise argparse.ArgumentTypeError(
                f"must be greater than 0: '{n}'",
            )
        else:
            return n

    def unsigned_int(value: str) -> int:
        if (n := assure_int(value)) < 0:
            raise argparse.ArgumentTypeError(
                f"must be greater than or equal to 0: '{n}'",
            )
        else:
            return n

    client_argument_group = parser.add_argument_group(title="client options")

    client_argument_group.add_argument(
        "--api-version",
        action=Once,
        choices=["dictation", "v1", "v1p1"],
        default="v1p1",
        help="the API version to communicate with the service; one of: %(choices)s (default is %(default)r)",
    )
    client_argument_group.add_argument(
        "--service-address",
        "-s",
        action=Once,
        help="the address and the port of an ASR Service instance to connect to, e.g. 'localhost:50051'",
        metavar="arg",
        required=True,
        type=non_empty_str,
    )
    client_tls_argument_group = client_argument_group.add_mutually_exclusive_group()
    client_tls_argument_group.add_argument(
        "--tls",
        action="store_true",
        help="if set, one-way TLS is enabled with a root certificate file "
        "retrieved from the gRPC runtime's default location; "
        "mutually exclusive with the `--tls-dir` and any `--tls-*-file` options",
    )
    client_tls_argument_group.add_argument(
        "--tls-dir",
        action=Once,
        dest="tls_dir",
        help="the path to a directory containing TLS credential files; "
        "the encryption method depends on the directory contents ("
        "'ca.crt' - one-way TLS with server authentication using an X.509 CA certificate; "
        "'client.crt', 'client.key' - mutual TLS; "
        "'client.crt', 'client.key', 'ca.crt' - mutual TLS with server authentication using an X.509 CA certificate); "
        "mutually exclusive with the `--tls` and any `--tls-*-file` options",
        metavar="arg",
        type=non_empty_str,
    )
    client_argument_group.add_argument(
        "--tls-ca-cert-file",  # "-file" or -path" (?)
        action=Once,
        dest="tls_ca_cert_file",
        help="the path to a file containing an X.509 CA certificate used for server authentication; "
        "any intermediate CA certificate must be concatenated after the CA certificate; "
        "mutually exclusive with the `--tls` and `--tls-dir` options",
        metavar="arg",
        type=non_empty_str,
    )
    client_argument_group.add_argument(
        "--tls-cert-file",  # "-file" or -path" (?)
        action=Once,
        dest="tls_cert_file",
        help="the path to a file containing an X.509 certificate used for client authentication; "
        "it requires the '--tls-private-key-file' option to be set along; "
        "when these two options are used, mutual TLS is enabled; "
        "mutually exclusive with the `--tls` and `--tls-dir` options",
        metavar="arg",
        type=non_empty_str,
    )
    client_argument_group.add_argument(
        "--tls-private-key-file",  # "-file" or -path" (?)
        action=Once,
        dest="tls_private_key_file",
        help="the path to a file containing an X.509 private key matching "
        "the certificate from the file specified by the `--tls-cert-file` option; "
        "when these two options are used, mutual TLS is enabled; "
        "mutually exclusive with the `--tls` and `--tls-dir` options",
        metavar="arg",
        type=non_empty_str,
    )

    audio_argument_group = parser.add_argument_group(title="audio stream options")
    audio_source_argument_group = audio_argument_group.add_mutually_exclusive_group(required=True)
    audio_source_argument_group.add_argument(
        "--audio-mic",
        "-m",
        action="store_true",
        help="if set, a microphone audio stream is used; it requires "
        "the '--audio-stream-chunk-duration' option to be set and "
        "the '--audio-path' option not to be set along",
    )
    audio_argument_group.add_argument(
        "--audio-mic-sampling-rate",
        action=Once,
        default=16000,
        dest="audio_mic_sampling_rate_hz",
        help="the sampling rate for the microphone audio stream, in Hz (default is %(default)s)",
        metavar="arg",
        type=positive_int,
    )
    audio_source_argument_group.add_argument(
        "--audio-paths",
        "--audio-path",
        "-a",
        action="extend",
        help="the paths to audio files; if set, a file audio stream is used; "
        "every file is processed in a separate request; however, "
        "if the '--session-id' option is set, they are considered to be parts "
        "of the same session by the service; it requires "
        "the '--audio-mic' option not to be set along",
        metavar="arg",
        nargs="+",
        type=non_empty_str,
    )
    audio_argument_group.add_argument(
        "--audio-stream-chunk-duration",
        action=Once,
        dest="audio_stream_chunk_duration_ms",
        help="the duration for the chunks read from the audio stream, in ms; "
        "if not set when the '--audio-paths' option is set, the file audio "
        "stream reads the audio file in a single chunk",
        metavar="arg",
        type=positive_int,
    )
    audio_argument_group.add_argument(
        "--audio-stream-interval",
        action=Once,
        default=0,
        dest="audio_stream_interval_ms",
        help="the interval for reading the audio stream, in ms; if set to "
        "the value of the '--audio-stream-chunk-duration' option, the client "
        "simulates the real time streaming; it has no effect on the microphone "
        "stream (default is %(default)s)",
        metavar="arg",
        type=unsigned_int,
    )
    audio_argument_group.add_argument(
        "--audio-prepend-silence",
        action=Once,
        default=0,
        dest="audio_prepend_silence_ms",
        help="the duration of silence to prepend to the audio stream, in ms (default is %(default)s)",
        metavar="arg",
        type=unsigned_int,
    )
    audio_argument_group.add_argument(
        "--audio-append-silence",
        action=Once,
        default=0,
        dest="audio_append_silence_ms",
        help="the duration of silence to append to the audio stream, in ms (default is %(default)s)",
        metavar="arg",
        type=unsigned_int,
    )

    request_argument_group = parser.add_argument_group(title="request options")
    request_response_argument_group = request_argument_group.add_mutually_exclusive_group(required=False)
    request_response_argument_group.add_argument(
        "--enable-auto-hold-response",
        "--hold-responses",
        action="store_true",
        help="if set, the service holds responses to return them in a batch; mutually exclusive with the `--enable-held-responses-merging` option",
    )
    request_response_argument_group.add_argument(
        "--enable-held-responses-merging",
        "--merge-responses",
        action="store_true",
        help="if set, the service merges responses to return one; mutually exclusive with the `--enable-auto-hold-response` option",
    )
    request_argument_group.add_argument(
        "--enable-interim-results",
        "--interim-results",
        action="store_true",
        help="if set, interim speech recognition results are returned between final ones",
    )
    request_argument_group.add_argument(
        "--enable-single-utterance",
        "--single-utterance",
        action="store_true",
        help="if set, recognition stops when the end of the first utterance is detected",
    )
    request_argument_group.add_argument(
        "--enable-speech-recognition-time-alignment",
        "--speech-time-alignment",
        action="store_true",
        help="if set, speech recognition results provide time alignment details of individual words",
    )
    request_argument_group.add_argument(
        "--grpc-timeout",
        action=Once,
        dest="grpc_timeout_ms",
        help="the timeout for a gRPC connection to await a reply, in ms; https://grpc.io/docs/guides/deadlines/#deadlines-on-the-client",
        metavar="arg",
        type=unsigned_int,
    )
    request_argument_group.add_argument(
        "--max-hypotheses-for-softmax",
        action=Once,
        default=10,
        dest="max_hypotheses_for_softmax",
        help="Maximum number of hypotheses considered during softmax computation (default: 10). "
        "This value is always forwarded to the server; use a higher value for more accurate "
        "confidence scores at the cost of increased computation.",
        metavar="arg",
        type=unsigned_int,
    )
    request_argument_group.add_argument(
        "--mrcp-no-input-timeout",
        action=Once,
        default=5000,
        dest="mrcp_no_input_timeout_ms",
        help="the MRCPv2 timeout counterpart, in ms; 0 disables the timeout (default is %(default)s)",
        metavar="arg",
        type=unsigned_int,
    )
    request_argument_group.add_argument(
        "--mrcp-recognition-timeout",
        action=Once,
        default=10000,
        dest="mrcp_recognition_timeout_ms",
        help="the MRCPv2 timeout counterpart, in ms; 0 disables the timeout (default is %(default)s)",
        metavar="arg",
        type=unsigned_int,
    )
    request_argument_group.add_argument(
        "--mrcp-speech-complete-timeout",
        action=Once,
        default=2000,
        dest="mrcp_speech_complete_timeout_ms",
        help="the MRCPv2 timeout counterpart, in ms; 0 disables the timeout (default is %(default)s)",
        metavar="arg",
        type=unsigned_int,
    )
    request_argument_group.add_argument(
        "--mrcp-speech-incomplete-timeout",
        action=Once,
        default=4000,
        dest="mrcp_speech_incomplete_timeout_ms",
        help="the MRCPv2 timeout counterpart, in ms; 0 disables the timeout (default is %(default)s)",
        metavar="arg",
        type=unsigned_int,
    )
    request_argument_group.add_argument(
        "--mrcp-start-input-timers-interspace",
        action=Once,
        default=0,
        dest="start_input_timer_control_message_interspace",
        help="the number of audio stream chunks to send before sending "
        "the MRCPv2 Start-Input-Timers message counterpart (in a loop); "
        "0 disables the functionality and starts the timers automatically (default is %(default)s); "
        "unsupported if the '--api-version' option is set to 'dictation'",
        metavar="arg",
        type=unsigned_int,
    )
    request_argument_group.add_argument(
        "--enable-all-recognition",
        "--all",
        action="store_true",
        dest="enable_all_recognition",
        help="if set, all recognition is requested",
    )
    request_argument_group.add_argument(
        "--enable-age-recognition",
        "--age",
        "-A",
        action="store_true",
        dest="enable_age_recognition",
        help="if set, age recognition is requested",
    )
    request_argument_group.add_argument(
        "--enable-gender-recognition",
        "--gender",
        "-G",
        action="store_true",
        dest="enable_gender_recognition",
        help="if set, gender recognition is requested",
    )
    request_argument_group.add_argument(
        "--enable-language-recognition",
        "--language",
        "-L",
        action="store_true",
        dest="enable_language_recognition",
        help="if set, language recognition is requested",
    )
    request_argument_group.add_argument(
        "--session-id",
        action=Once,
        help="the ID of the session; if not set, the service generates an ID "
        "itself; it makes it possible to concatenate data from multiple requests "
        "as long as the service's cache is enabled",
        default="",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--speech-recognition-alternatives-limit",
        "--speech-alternatives",
        action=Once,
        help="the limit of speech recognition alternatives to be returned in "
        "a single result; the actual count of returned alternatives may be lower "
        "(0 as well); if set to 0, the service implicitly treats it as 1",
        default=1,
        metavar="arg",
        type=unsigned_int,
    )
    # TODO:
    # ```
    # request_argument_group.add_argument(
    #     "--speech-recognition-language-group-names",
    #     "--languages",
    #     action="append",
    #     help="the ordered names of language groups to be used for speech "
    #     "recognition; if one of the groups is not found, the service tries to "
    #     "use another; if not set, the service uses its default group",
    #     metavar="arg",
    #     nargs="+",
    #     type=str,
    # )
    request_argument_group.add_argument(
        "--speech-recognition-language-group-name",
        "--speech-language-group",
        action=Once,
        help="the name of the language group to be used for speech recognition; if not set, the service uses its default group",
        metavar="arg",
        type=str,
    )
    # ```
    # TODO:
    # ```
    # request_argument_group.add_argument(
    #     "--speech-recognition-model-names",
    #     "--speech-models",
    #     action="append",
    #     help="the ordered names of models to be used for speech recognition; "
    #     "if one of the models is not found, the service tries to use another; "
    #     "if none is found, recognition is not performed; if not set, "
    #     "the service uses its default model",
    #     metavar="arg",
    #     nargs="+",
    #     type=str,
    # )
    # ```
    request_argument_group.add_argument(
        "--speech-recognition-model-name",
        "--speech-model",
        action=Once,
        help="the name of the model to be used for speech recognition; if not set, the service uses its default model",
        metavar="arg",
        type=str,
    )
    # session config for decoder
    request_argument_group.add_argument(
        "--decoder.beam-size",
        dest="decoder__beam_size",
        default="NA",
        help="Set decoder.beam-size (int) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--decoder.beam-size-token",
        dest="decoder__beam_size_token",
        default="NA",
        help="Set decoder.beam-size-token (int) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--decoder.beam-threshold",
        dest="decoder__beam_size_threshold",  # TODO: dest has spurious 'size'; kwarg passed to builder is decoder__beam_threshold (correct server key)
        default="NA",
        help="Set decoder.beam-threshold (double) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--decoder.lm-weight",
        dest="decoder__lm_weight",
        default="NA",
        help="Set decoder.lm-weight (double) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--decoder.word-score",
        dest="decoder__word_score",
        default="NA",
        help="Set decoder.word-score (double) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--decoder.sil-score",
        dest="decoder__sil_score",
        default="NA",
        help="Set decoder.sil-score (double) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--decoder.log-add",
        dest="decoder__log_add",
        default="NA",
        help="Set decoder.log_add (bool) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--decoder.criterion-type",
        dest="decoder__criterion_type",
        default="NA",
        help="Set decoder.criterion type (value in {S2S, CTC, ASG}) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--decoder.trie.smearing-mode",
        dest="decoder__trie__smearing_mode",
        default="NA",
        help="Set decoder.trie.smearing-mode (value in {NONE, MAX, LOGADD}) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--decoder.trie.tokenizer-type",
        dest="decoder__trie__tokenizer_type",
        default="NA",
        help="Set decoder.trie.tokenizer-type for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--decoder.trie.best-spellings",
        dest="decoder__trie__best_spellings",
        default="NA",
        help="Set decoder.trie.best_spellings (unsigned long) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--postprocessor-min-sil-duration-ms",
        dest="postprocessor_min_sil_duration_ms",
        default="NA",
        help="Set postprocessor-min-sil-duration-ms (unsigned long) for session",
        metavar="arg",
        type=str,
    )

    # session config for detector
    request_argument_group.add_argument(
        "--extractor.sampling-frequency",
        dest="extractor__sampling_frequency",
        default="NA",
        help="Set extractor.sampling-frequency (float) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--detector.minimal-speech-duration",
        dest="detector__minimal_speech_duration",
        default="NA",
        help="Set detector.minimal_speech_duration (unsigned int) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--detector.minimal-silence-duration",
        dest="detector__minimal_silence_duration",
        default="NA",
        help="Set detector.minimal-silence-duration (unsigned int) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--detector.speech-padding",
        dest="detector__speech_padding",
        default="NA",
        help="Set detector.speech-padding (unsigned int) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--detector.speech-threshold",
        dest="detector__speech_threshold",
        default="NA",
        help="Set detector.speech-threshold (float) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--detector.silence-threshold",
        dest="detector__silence_threshold",
        default="NA",
        help="Set detector.silence-threshold (float) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--detector.alignment-speech-duration",
        dest="detector__alignment_speech_duration",
        default="NA",
        help="Set detector.alignment-speech-duration (float) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--detector.minimal-alignment-speech-duration",
        dest="detector__minimal_alignment_speech_duration",
        default="NA",
        help="Set detector.minimal_alignment_speech_duration (unsigned int) for session",
        metavar="arg",
        type=str,
    )
    request_argument_group.add_argument(
        "--detector.minimal-alignment-silence-duration",
        dest="detector__minimal_alignment_silence_duration",
        default="NA",
        help="Set detector.minimal-alignment-silence-duration (unsigned int) for session",
        metavar="arg",
        type=str,
    )

    args = parser.parse_args()
    args.enable_manual_input_timer = args.start_input_timer_control_message_interspace > 0

    if args.audio_mic and not args.audio_stream_chunk_duration_ms:
        parser.error("argument --audio-mic/-m: argument --audio-stream-chunk-duration is required")

    if args.tls and any((args.tls_ca_cert_file, args.tls_cert_file, args.tls_private_key_file)):
        parser.error("argument --tls: not allowed with any argument --tls-*-file")

    if args.tls_dir and any((args.tls_ca_cert_file, args.tls_cert_file, args.tls_private_key_file)):
        parser.error("argument --tls-dir: not allowed with any argument --tls-*-file")

    if args.tls_cert_file and not args.tls_private_key_file:
        parser.error("argument --tls-cert-file: argument --tls-private-key-file is required")

    if args.tls_private_key_file and not args.tls_cert_file:
        parser.error("argument --tls-private-key-file: argument --tls-cert-file is required")

    return args


def _as_dict(**kwargs) -> dict[str, int]:
    timeouts = dict()

    if "no_input_timeout_ms" in kwargs:
        timeouts["no-input-timeout"] = kwargs.get("no_input_timeout_ms")

    if "recognition_timeout_ms" in kwargs:
        timeouts["recognition-timeout"] = kwargs.get("recognition_timeout_ms")

    if "speech_complete_timeout_ms" in kwargs:
        timeouts["speech-complete-timeout"] = kwargs.get("speech_complete_timeout_ms")

    if "speech_incomplete_timeout_ms" in kwargs:
        timeouts["speech-incomplete-timeout"] = kwargs.get("speech_incomplete_timeout_ms")

    return timeouts


def build_additional_config_specs_dict(**kwargs) -> dict[str, str]:
    built_dict: dict[str, str] = {}
    for arg_name, arg_val in kwargs.items():
        if arg_val != "NA":
            actual_arg_name = arg_name.replace("__", ".").replace("_", "-")
            built_dict[actual_arg_name] = str(arg_val)

    return built_dict


def main():
    args = parse_args()

    if not args.quiet:
        print(legal_header)

    if args.audio_mic:
        audio_streams = [
            audio_processing.MicrophoneStream(
                sampling_rate_hz=args.audio_mic_sampling_rate_hz,
                chunk_duration_ms=args.audio_stream_chunk_duration_ms,
                prepend_silence_ms=args.audio_prepend_silence_ms,
                append_silence_ms=args.audio_append_silence_ms,
            )
        ]
        audio_sources = ["-"]
    else:
        audio_streams = (
            audio_processing.AudioFileStream(
                audio_path,
                chunk_duration_ms=args.audio_stream_chunk_duration_ms,
                prepend_silence_ms=args.audio_prepend_silence_ms,
                append_silence_ms=args.audio_append_silence_ms,
            )
            for audio_path in args.audio_paths
        )
        audio_sources = args.audio_paths

    if any(
        (
            args.tls,
            args.tls_ca_cert_file,
            args.tls_cert_file,
            args.tls_dir,
            args.tls_private_key_file,
        )
    ):
        ca_cert_file_path = args.tls_ca_cert_file or (Path(args.tls_dir) / "ca.crt" if args.tls_dir else None)

        private_key_file_path = args.tls_private_key_file or (Path(args.tls_dir) / "client.key" if args.tls_dir else None)

        cert_file_path = args.tls_cert_file or (Path(args.tls_dir) / "client.crt" if args.tls_dir else None)

        def try_read(path):
            return Path(path).read_bytes() if path else None

        grpc_channel_credentials = create_grpc_channel_credentials(
            tls_certificate_chain=try_read(cert_file_path),
            tls_private_key=try_read(private_key_file_path),
            tls_root_certificates=try_read(ca_cert_file_path),
        )
    else:
        grpc_channel_credentials = None

    with create_grpc_channel(args.service_address, credentials=grpc_channel_credentials) as grpc_channel:
        if args.api_version == "dictation":
            asr_stub = dictation.Asr(grpc_channel)
        elif args.api_version == "v1":
            asr_stub = v1.Asr(grpc_channel, api_patch_version=None)
        elif args.api_version == "v1p1":
            asr_stub = v1.Asr(grpc_channel, api_patch_version=1)
        else:
            raise AssertionError(f"unknown api_version: {args.api_version}")

        @contextlib.contextmanager
        def cancel_grpc_stream_signal_handler():
            default_sigint_handler: signal.Handlers = signal.SIG_DFL
            try:

                def cancel_grpc_stream_callback(_, __):
                    if not args.quiet:
                        print("...")

                    try:
                        grpc_stream.cancel()
                    except NameError:
                        pass

                default_sigint_handler = signal.signal(signal.SIGINT, cancel_grpc_stream_callback)  # type: ignore[assignment]

                yield
            except:
                raise
            finally:
                signal.signal(signal.SIGINT, default_sigint_handler)

        for audio_stream, audio_source in zip(audio_streams, audio_sources):
            if not args.quiet:
                print(audio_source)

            grpc_stream = asr_stub.streaming_recognize(
                audio_stream=audio_stream,
                audio_stream_interval_ms=args.audio_stream_interval_ms,
                grpc_timeout_ms=args.grpc_timeout_ms,
                session_id=args.session_id,
                enable_age_recognition=args.enable_age_recognition or args.enable_all_recognition,
                enable_auto_hold_response=args.enable_auto_hold_response,
                enable_gender_recognition=args.enable_gender_recognition or args.enable_all_recognition,
                enable_held_responses_merging=args.enable_held_responses_merging,
                enable_interim_results=args.enable_interim_results,
                enable_language_recognition=args.enable_language_recognition or args.enable_all_recognition,
                enable_manual_input_timer=args.enable_manual_input_timer,
                enable_single_utterance=args.enable_single_utterance,
                enable_speech_recognition_time_alignment=args.enable_speech_recognition_time_alignment,
                speech_recognition_alternatives_limit=args.speech_recognition_alternatives_limit,
                speech_recognition_language_group_name=args.speech_recognition_language_group_name,
                speech_recognition_model_name=args.speech_recognition_model_name,
                start_input_timer_control_message_interspace=args.start_input_timer_control_message_interspace,
                timeouts=_as_dict(
                    no_input_timeout_ms=args.mrcp_no_input_timeout_ms,
                    recognition_timeout_ms=args.mrcp_recognition_timeout_ms,
                    speech_complete_timeout_ms=args.mrcp_speech_complete_timeout_ms,
                    speech_incomplete_timeout_ms=args.mrcp_speech_incomplete_timeout_ms,
                ),
                additional_config_specs=build_additional_config_specs_dict(
                    decoder__beam_size=args.decoder__beam_size,
                    decoder__beam_size_token=args.decoder__beam_size_token,
                    decoder__beam_threshold=args.decoder__beam_size_threshold,
                    decoder__lm_weight=args.decoder__lm_weight,
                    decoder__word_score=args.decoder__word_score,
                    decoder__sil_score=args.decoder__sil_score,
                    decoder__log_add=args.decoder__log_add,
                    decoder__criterion_type=args.decoder__criterion_type,
                    decoder__trie__smearing_mode=args.decoder__trie__smearing_mode,
                    decoder__trie__tokenizer_type=args.decoder__trie__tokenizer_type,
                    decoder__trie__best_spellings=args.decoder__trie__best_spellings,
                    postprocessor_min_sil_duration_ms=args.postprocessor_min_sil_duration_ms,
                    max_hypotheses_for_softmax=args.max_hypotheses_for_softmax,
                    extractor__sampling_frequency=args.extractor__sampling_frequency,
                    detector__minimal_speech_duration=args.detector__minimal_speech_duration,
                    detector__minimal_silence_duration=args.detector__minimal_silence_duration,
                    detector__speech_padding=args.detector__speech_padding,
                    detector__speech_threshold=args.detector__speech_threshold,
                    detector__silence_threshold=args.detector__silence_threshold,
                    detector__alignment_speech_duration=args.detector__alignment_speech_duration,
                    detector__minimal_alignment_speech_duration=args.detector__minimal_alignment_speech_duration,
                    detector__minimal_alignment_silence_duration=args.detector__minimal_alignment_silence_duration,
                ),
            )
            with cancel_grpc_stream_signal_handler():
                try:
                    if not args.quiet:
                        for metadatum in grpc_stream.initial_metadata():
                            print(metadatum[0], metadatum[1], sep=": ")

                    for response in grpc_stream:  # type: ignore
                        print(
                            json_format.MessageToJson(
                                response,
                                ensure_ascii=False,
                                always_print_fields_with_no_presence=True,
                            )
                        )
                except grpc.RpcError as error:
                    print(error)
                finally:
                    if not args.quiet:
                        for metadatum in grpc_stream.trailing_metadata():
                            print(metadatum[0], metadatum[1], sep=": ")


if __name__ == "__main__":
    main()
