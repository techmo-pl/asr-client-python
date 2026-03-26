from unittest.mock import patch

import pytest

from asr_client.__main__ import main


def test_cli_help_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["asr-client", "--help"]):
            main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "--service-address" in captured.out


def test_cli_requires_service_address() -> None:
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["asr-client"]):
            main()
    assert exc_info.value.code != 0


def test_cli_prepend_silence_flag() -> None:
    from asr_client.__main__ import parse_args

    with patch("sys.argv", ["asr-client", "--service-address", "localhost:50051", "--audio-paths", "x.wav", "--audio-prepend-silence", "150"]):
        args = parse_args()
    assert args.audio_prepend_silence_ms == 150


def test_cli_append_silence_flag() -> None:
    from asr_client.__main__ import parse_args

    with patch("sys.argv", ["asr-client", "--service-address", "localhost:50051", "--audio-paths", "x.wav", "--audio-append-silence", "150"]):
        args = parse_args()
    assert args.audio_append_silence_ms == 150
