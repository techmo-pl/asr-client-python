# Changelog of ASR Client (Python)


## [1.6.0] - 2026-03-24 (#76)

### Added

- cli / audio
  - `--audio-prepend-silence <ms>`: prepends the given number of milliseconds of zero-filled PCM silence to the audio stream before sending to the ASR service; works for both `--audio-paths` (file streams) and `--audio-mic` (microphone streams); useful for priming the detector when the utterance starts immediately at the beginning of the audio
  - `--audio-append-silence <ms>`: appends the given number of milliseconds of zero-filled PCM silence to the audio stream; works for both `--audio-paths` (file streams) and `--audio-mic` (microphone streams); useful for ensuring the detector has enough trailing silence to finalise the last utterance


## [1.5.6] - 2026-03-23 (#75)

### Added

- scripts
  - `install.sh`: preflight checks for `uv`, `gcc`, `python3-dev`, and `portaudio19-dev` with targeted error messages and the exact `apt install` command; all checks run before creating the virtualenv so a fresh machine reports every missing package in one pass

### Changed

- documentation
  - `README.md`: `uv` added to Requirements; Install section updated to show `./install.sh` as primary path with uv-based manual alternative; outdated `python3 -m venv` + `pip` workflow removed
  - `install.sh`, `README.md`, `doc/DOCUMENTATION.md`: `uv` install method updated from `pip3 install uv` to the canonical standalone installer (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
  - `doc/DOCUMENTATION.md`: added "Missing uv" troubleshooting entry


## [1.5.5] - 2026-03-23

### Fixed

- ci
  - authentication issues with submodule cloning in certain CI environments

### Changed

- submodules
  - `asr-api-python` updated to 1.1.4


## [1.5.4] - 2026-03-10 (#72)

### Fixed

- _asr_client_ package
  - `pydub` `SyntaxWarning` suppression ineffective on first run after install: `filterwarnings(module=r"pydub")` did not match compile-time warnings (which use the source file path as the module identifier); replaced with `warnings.catch_warnings()` + `simplefilter("ignore", SyntaxWarning)` scoped around the `import pydub` statement


## [1.5.3] - 2026-03-06 (#71)

### Fixed

- _asr_client_ package
  - `pydub` emitting `SyntaxWarning` for invalid escape sequences on Python 3.14; suppressed via `warnings.filterwarnings` in `audio_processing.py` before `pydub` is imported
  - type annotations: `CallCredentials` → `ChannelCredentials` and `str | None` → `bytes | None` for TLS parameters in `__init__.py`; walrus operator variable shadowing in `__main__.py`; `Once.__call__` missing default; `asr_stub` and `default_sigint_handler` possibly-unbound; `_fill_audio_buffer` return type


## [1.5.2] - 2026-03-05 (#70)

### Fixed

- _asr_client_ package
  - `MessageToJson()` call using removed parameter `including_default_value_fields`; replaced with `always_print_fields_with_no_presence` (protobuf ≥ 4.x API change)

### Added

- tests
  - `tests/test_integration.py` — integration tests invoking the CLI against a live ASR service for all three API versions (`v1p1`, `v1`, `dictation`)
  - `data/audio.wav` — bundled test audio fixture
  - `--asr-service-address` pytest option (registered in `conftest.py`) to enable integration tests; skipped automatically when not provided
- CI
  - `test_integration` job running integration tests in a parallel matrix over Python 3.8–3.13 (3.14 with `allow_failure`)
  - consolidated `test_py314` into the `test` matrix using per-instance `rules: allow_failure`


## [1.5.1] - 2026-03-05 (#69)

### Changed

- submodules
  - asr-api-python (1.1.3)
- CI
  - removed `setup_uv` job — `uv` is now pre-installed on runners
  - unified coverage regex to handle decimal values
  - added coverage artifacts to `test_py314` job (were silently discarded before)
  - extended test matrix from 3.10–3.13 to 3.8–3.13 (mirrors asr-api-python range)
- dependencies
  - grpcio: `>=1.63.0,<1.71.0` for Python 3.8 (1.71 dropped 3.8), `>=1.63.0` for 3.9+ (required for protobuf 5 compatibility)
  - protobuf: bumped to `>=5.26.0,<6` (required by asr-api-python 1.1.3 generated stubs)
  - requires-python lowered from `>=3.10` to `>=3.8`
- _asr_client_ package
  - added `from __future__ import annotations` to all modules (enables `X | Y` union syntax on Python 3.8+)
  - replaced `zip(..., strict=False)` with `zip(...)` — `strict=` parameter was added in Python 3.10

### Added

- `install.sh` — creates virtualenv and installs package with test dependencies


## [1.5.0] - 2026-02-28 (#60)

### Added

- changing all zipformer models configurations is now possible at runtime for each session, information on how to do it exactly provided via --help flag


## [1.4.2] - 2026-02-09 (#68)

### Changed

- dependencies
  - introduced upper bound on setuptools to lower than 82 because of drop of pkg_resources
- submodules
  - asr-api-python (v1.1.2)


## [1.4.1] - 2026-02-07 (#67)

### Fixed

- dependencies
    - introduced pip<26 constraint until pip-tools will release tag for https://github.com/jazzband/pip-tools/pull/2320


## [1.4.0] - 2024-09-04 (#64)

### Changed

- default API version for requests changed from `v1` to `v1p1`


## [1.3.4] - 2024-09-04 (#57)

### Changed

- dependencies
  - lower and upper bound on grpcio requirement to be more or equal to 1.49.4 and less than 1.63
  - lower and upper bound on protobuf requirement to be more or equal to 4.21.3 and less than 5
- submodules
  - asr-api-python (v1.1.1)

### Removed

- releases
  - withdrawn [1.3.2](#132---2024-09-02-withdrawn) and [1.3.3](#133---2024-09-02-56-withdrawn) releases due to wrong protobuf requirement bounds (#57)

### Fixed

- releases
  - inaccurate changelog description of [1.3.3](#133---2024-09-02-56-withdrawn) release


## [1.3.3] - 2024-09-02 (#56, withdrawn)

### Fixed

- _asr_client_ package
  - outdated parameter name `including_default_value_fields` in `google.protobuf.json_format.MessageToDict` function causing application to crash due to incompatibility with protobuf (>=5) (#56)


## [1.3.2] - 2024-09-02 (#55, withdrawn)

### Changed

- dependencies
  - upper bound on protobuf requirement to be less than 5.28 (#55)
- submodules
  - asr-api-python (@04f67e7)


## [1.3.1] - 2024-05-28

### Fixed

- _asr_client_ package
  - missing verification of timeout existence in _techmo.asr.api.dictation_ API (#52)


## [1.3.0] - 2024-05-15

### Added

- _asr_client_ package
  - support for _techmo.asr.api.v1p1_ API (#46)
  - CLI `--enable-auto-hold-response`, `--enable-held-responses-merging` parameters to utilize response holding and merging functionality of _techmo.asr.api.v1p1_ API (#46)
  - CLI `--tls` flag to use TLS certificate from default location (#44)
  - CLI `--tls-ca-cert-file`, `--tls-cert-file`, `--tls-private-key-file` parameters to enable direct selection of TLS files (#44)

### Fixed

- Docker image build in CI


## [1.2.0] - 2024-04-08

### Added

- _asr_client_ package
  - CLI `--mrcp-start-input-timers-interval` parameter to utilize manual input timers functionality of _techmo.asr.api.v1_ API (#35)
  - CLI `--enable-all-recognition` parameter to request all recognition modules (#37)

### Changed

- _asr_client_ package
  - renamed CLI `--no-age-recognition`, `--no-gender-recognition`, `--no-language-recognition` parameters into `--enable-age-recognition`, `--enable-gender-recognition`, `--enable-language-recognition` and toggled their behavior (#37)


## [1.1.2] - 2024-04-05

### Added

- Dockerfile for deployment (#33)

## Fixed

- _asr_client_ package
  - CLI `--session-id` parameter causing application to crash (#36, #38)


## [1.1.1] - 2024-02-29

### Fixed

- _asr_client_ package
  - MRCPv2 timeouts not always sent with _techmo.asr.api.dictation_ API (#32)


## [1.1.0] - 2024-01-30

### Added

- _asr_client_ package
  - support for _techmo.asr.api.dictation_ API (#18)
- submodules
  - asr-api-python (v1.0.0)

### Changed

- _asr_client_ package
  - CLI description for `--audio-mic` parameter to mention `--audio-stream-chunk-duration` parameter (#20)
  - CLI description for `--grpc-timeout` parameter to refer to gRPC documentation (#20)
  - CLI description for `--mrcp-no-input-timeout`, `--mrcp-recognition-timeout`, `--mrcp-speech-complete-timeout`, `--mrcp-speech-incomplete-timeout` to explain behavior of `0` argument (#20)

### Fixed

- _asr_client_ package
  - unreliable cancelling of gRPC stream with SIGINT (#22)
  - CLI allowing multiple parameter occurrences but implicitly parsing only last one (#26)
  - CLI allowing negative values for `--audio-stream-interval`, `--grpc-timeout`, `--mrcp-no-input-timeout`, `--mrcp-recognition-timeout`, `--mrcp-speech-complete-timeout`, `--mrcp-speech-incomplete-timeout`, `--speech-recognition-alternatives-limit` parameters (#21, #24, #25)
  - CLI allowing nonpositive values for `--audio-mic-sampling-rate`, `--audio-stream-chunk-duration` parameters (#21)
  - CLI incorrect description for `--tls-dir` parameter to list _client.crt_, _client.key_ files instead of _server.crt_, _server.key_
- changelog
    - description of [v1.0.0](#100---2023-11-23) release

### Removed

- submodules
  - asr-api


## [1.0.0] - 2023-11-23

### Added

- _asr_client_ package
  - support for _techmo.asr.api.v1_ API (#15)
- documentation
- Setuptools configuration
- CI configuration
- submodules
  - asr-api (v1.0.0-beta.1)
