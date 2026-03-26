# Changelog of ASR Client (Python)


## [1.6.0] - 2026-03-24

### Added

- `asr_client/__main__.py`: `--audio-prepend-silence <ms>` option: prepends zero-filled PCM silence to the audio stream before sending to the ASR service; works for both `--audio-paths` and `--audio-mic`; useful for priming the detector when the utterance starts immediately at the beginning of the audio.
- `asr_client/__main__.py`: `--audio-append-silence <ms>` option: appends zero-filled PCM silence to the audio stream; works for both `--audio-paths` and `--audio-mic`; useful for ensuring the detector has enough trailing silence to finalise the last utterance.


## [1.5.6] - 2026-03-23

### Added

- `install.sh`: preflight checks for `uv`, `gcc`, `python3-dev`, and `portaudio19-dev` with targeted error messages and the exact `apt install` command; all checks run before creating the virtualenv so a fresh machine reports every missing package in one pass.

### Changed

- `README.md`: `uv` added to Requirements; Install section updated to show `./install.sh` as primary path; outdated `python3 -m venv` and `pip` workflow removed.
- `install.sh`, `README.md`, `doc/DOCUMENTATION.md`: `uv` install method updated to the canonical standalone installer (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- `doc/DOCUMENTATION.md`: added "Missing uv" troubleshooting entry.


## [1.5.5] - 2026-03-23

### Fixed

- CI: resolved authentication issues with submodule cloning in certain environments.

### Changed

- `submodules/asr-api-python`: updated to 1.1.4.


## [1.5.4] - 2026-03-10

### Fixed

- `asr_client/audio_processing.py`: `pydub` `SyntaxWarning` suppression ineffective on first run after install; replaced `filterwarnings(module=r"pydub")` with `warnings.catch_warnings()` + `simplefilter("ignore", SyntaxWarning)` scoped around the `import pydub` statement.


## [1.5.3] - 2026-03-06

### Fixed

- `asr_client/audio_processing.py`: suppressed `pydub` `SyntaxWarning` for invalid escape sequences on Python 3.14.
- `asr_client/__init__.py`: corrected type annotations (`CallCredentials` → `ChannelCredentials`, `str | None` → `bytes | None` for TLS parameters).
- `asr_client/__main__.py`: fixed walrus operator variable shadowing; `asr_stub` and `default_sigint_handler` possibly-unbound; `_fill_audio_buffer` return type; `Once.__call__` missing default.


## [1.5.2] - 2026-03-05

### Fixed

- `asr_client/`: `MessageToJson()` call using removed parameter `including_default_value_fields`; replaced with `always_print_fields_with_no_presence` (protobuf ≥ 4.x API change).

### Added

- `tests/test_integration.py`: integration tests invoking the CLI against a live ASR service for all three API versions (`v1p1`, `v1`, `dictation`).
- `data/audio.wav`: bundled test audio fixture.
- `conftest.py`: `--asr-service-address` pytest option to enable integration tests; skipped automatically when not provided.
- `.github/workflows/test.yml`: `test_integration` job running integration tests in a parallel matrix over Python 3.8–3.13.


## [1.5.1] - 2026-03-05

### Added

- `install.sh`: creates virtualenv and installs package with test dependencies.

### Changed

- `submodules/asr-api-python`: updated to 1.1.3.
- `pyproject.toml`: grpcio bounds updated for Python 3.8 (`>=1.63.0,<1.71.0` for 3.8, `>=1.63.0` for 3.9+); protobuf bumped to `>=5.26.0,<6`; `requires-python` lowered to `>=3.8`.
- `asr_client/`: added `from __future__ import annotations` to all modules; replaced `zip(..., strict=False)` with `zip(...)` for Python 3.8 compatibility.
- `.github/workflows/test.yml`: test matrix extended from Python 3.10–3.13 to 3.8–3.13.


## [1.5.0] - 2026-02-28

### Added

- `asr_client/`: changing all zipformer model configurations is now possible at runtime for each session via CLI parameters.


## [1.4.2] - 2026-02-09

### Changed

- `pyproject.toml`: introduced upper bound on setuptools below 82 due to removal of `pkg_resources`.
- `submodules/asr-api-python`: updated to v1.1.2.


## [1.4.1] - 2026-02-07

### Fixed

- `pyproject.toml`: added `pip<26` constraint pending upstream pip-tools compatibility fix.


## [1.4.0] - 2024-09-04

### Changed

- `asr_client/`: default API version for requests changed from `v1` to `v1p1`.


## [1.3.4] - 2024-09-04

### Changed

- `pyproject.toml`: grpcio requirement bounds set to `>=1.49.4,<1.63`; protobuf requirement bounds set to `>=4.21.3,<5`.
- `submodules/asr-api-python`: updated to v1.1.1.


## [1.3.3] - 2024-09-02 (withdrawn)

### Fixed

- `asr_client/`: outdated parameter name `including_default_value_fields` in `google.protobuf.json_format.MessageToDict` causing crash with protobuf ≥ 5.


## [1.3.2] - 2024-09-02 (withdrawn)

### Changed

- `pyproject.toml`: upper bound on protobuf set to less than 5.28.


## [1.3.1] - 2024-05-28

### Fixed

- `asr_client/`: missing verification of timeout existence in the _techmo.asr.api.dictation_ API.


## [1.3.0] - 2024-05-15

### Added

- `asr_client/`: support for _techmo.asr.api.v1p1_ API.
- `asr_client/__main__.py`: `--enable-auto-hold-response` and `--enable-held-responses-merging` parameters for the v1p1 response hold/merge functionality.
- `asr_client/__main__.py`: `--tls` flag for TLS certificate from default location.
- `asr_client/__main__.py`: `--tls-ca-cert-file`, `--tls-cert-file`, `--tls-private-key-file` parameters for direct TLS file selection.


## [1.2.0] - 2024-04-08

### Added

- `asr_client/__main__.py`: `--mrcp-start-input-timers-interval` parameter for manual input timers in the _techmo.asr.api.v1_ API.
- `asr_client/__main__.py`: `--enable-all-recognition` parameter to request all recognition modules.

### Changed

- `asr_client/__main__.py`: renamed `--no-age-recognition`, `--no-gender-recognition`, `--no-language-recognition` to `--enable-age-recognition`, `--enable-gender-recognition`, `--enable-language-recognition` with toggled behavior.


## [1.1.2] - 2024-04-05

### Added

- `Dockerfile`: added for deployment.

### Fixed

- `asr_client/__main__.py`: `--session-id` parameter causing application to crash.


## [1.1.1] - 2024-02-29

### Fixed

- `asr_client/`: MRCPv2 timeouts not always sent with the _techmo.asr.api.dictation_ API.


## [1.1.0] - 2024-01-30

### Added

- `asr_client/`: support for _techmo.asr.api.dictation_ API.
- `submodules/asr-api-python`: added asr-api-python v1.0.0.

### Changed

- `asr_client/__main__.py`: updated CLI descriptions for `--audio-mic`, `--grpc-timeout`, and MRCPv2 timeout parameters to clarify behaviour of the `0` argument.

### Fixed

- `asr_client/`: unreliable cancelling of gRPC stream with SIGINT.
- `asr_client/__main__.py`: CLI allowing multiple parameter occurrences but parsing only the last one.
- `asr_client/__main__.py`: CLI allowing negative values for `--audio-stream-interval`, `--grpc-timeout`, and MRCPv2 timeout parameters.
- `asr_client/__main__.py`: CLI allowing nonpositive values for `--audio-mic-sampling-rate` and `--audio-stream-chunk-duration`.
- `asr_client/__main__.py`: incorrect description for `--tls-dir` listing wrong certificate files.


## [1.0.0] - 2023-11-23

### Added

- `asr_client/`: support for _techmo.asr.api.v1_ API.
- Documentation.
- `pyproject.toml`: setuptools configuration.
- CI configuration.
- `submodules/asr-api-python`: added asr-api-python v1.0.0.
