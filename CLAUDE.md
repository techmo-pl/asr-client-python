# CLAUDE.md — asr-client-python

## Project Overview

**asr-client-python** is a gRPC client library and CLI tool for the Techmo ASR (Automatic Speech Recognition) Service. It wraps the `asr-api-python` Python bindings (from `techmo-asr-api` on GitHub) into a user-facing package with:
- A Python API (`asr_client` package)
- A CLI tool (`asr-client` entry point → `asr_client.__main__:main`)

Current version: see `asr_client/VERSION.py` (`__version__` attribute).

---

## Repository Setup (run once after cloning)

```bash
./setup.sh    # Install pre-commit hooks
./install.sh  # Create .venv + install package with test extras
```

- `setup.sh` — clones the `techmo-pl/pre-commit` tooling from GitHub and installs hooks.
- `install.sh` — creates `.venv` via `uv`, runs `uv pip install -e ".[test]"`. Accepts an optional `VENV_PATH` argument (default: `.venv`). Checks upfront for `uv`, `gcc`, Python headers, and PortAudio headers — fails with a clear message if any are missing.

---

## Package Architecture

```
asr_client/
├── __init__.py          # Public API: create_grpc_channel(), create_grpc_channel_credentials(),
│                        # and the _generate_request_with_traceback decorator
├── __main__.py          # CLI entry point: argument parsing, TLS, streaming logic
├── audio_processing.py  # AudioFile, AudioStream, AudioFileStream, MicrophoneStream
├── v1.py                # v1 and v1p1 API implementation
├── dictation.py         # Legacy dictation API implementation
└── VERSION.py           # __version__ attribute
```

### API version map

| `--api-version` value | Module | gRPC stub | Response key |
|----------------------|--------|-----------|--------------|
| `v1p1` (default) | `v1.py` | `asr_api.v1p1.AsrStub` | `"result"` |
| `v1` | `v1.py` | `asr_api.v1.AsrStub` | `"result"` |
| `dictation` | `dictation.py` | `asr_api.dictation.SpeechStub` | `"results"` (plural) |

`v1` and `v1p1` share `v1.py`; the stub is selected via `api_patch_version` (`None` → v1, `1` → v1p1).

**Session ID metadata key differs by API version:** `v1`/`v1p1` sends gRPC metadata key `"session-id"` (hyphen); `dictation` sends `"session_id"` (underscore). Do not change either without verifying the server-side expectation.

---

## gRPC / Protobuf Rules

- Generated protobuf files (`*_pb2.py`, `*_pb2_grpc.py`) are produced at install time — never commit them.
- All gRPC stubs are imported via `from asr_api import v1, v1p1, dictation`. The `asr_api` package is installed from `techmo-asr-api @ git+https://github.com/techmo-pl/asr-api-python.git@1.1.4` (declared in `pyproject.toml` dependencies).
- If `asr_api` imports fail after cloning, run `./install.sh`.

---

## Key Dependency

| Package | Source |
|---------|--------|
| `techmo-asr-api` | `git+https://github.com/techmo-pl/asr-api-python.git@1.1.4` — gRPC stubs for all ASR API versions (the `asr_api` Python package) |

---

## System Prerequisites

Before `./install.sh` can succeed on a fresh machine (Debian/Ubuntu):

```bash
apt install python3-dev portaudio19-dev build-essential
```

`python3-dev` and `build-essential` are needed to compile `pyaudio`'s C extension; `portaudio19-dev` provides the PortAudio headers. `./install.sh` checks all three and fails with a clear message if any are missing.

---

## Dependencies — Sharp Edges

| Dependency | Why it matters |
|-----------|----------------|
| `audioop-lts` | `audioop` removed from stdlib in Python 3.13; conditional dep for `python_version >= '3.13'` |
| `pydub` | Emits `SyntaxWarning` on Python 3.14 during import; suppressed with `warnings.catch_warnings()` in `audio_processing.py` — do not remove or move that guard |
| `grpcio` | Pinned `<1.71.0` for Python 3.8 only; unpinned on 3.9+ |
| `techmo-asr-api` | Installed from `git+https://github.com/techmo-pl/asr-api-python.git@1.1.4` |

**gRPC 4 MB message limit:** Default max incoming message size is 4 MB. Sending a file larger than ~4 MB as a single chunk will fail with `StatusCode.RESOURCE_EXHAUSTED`. Use `--audio-stream-chunk-duration` for large files.

---

## Testing

### Running tests

```bash
# Unit tests only (no service needed)
pytest tests/ -k "not integration"

# With coverage
pytest tests/ --cov=asr_client --cov-report=term-missing -k "not integration"

# Integration tests (requires a live ASR service)
pytest tests/test_integration.py --asr-service-address HOST:PORT

# Full tox matrix (Python 3.8–3.14)
tox

# Single version
tox -e py311

# Integration via tox
tox -e py311 -- tests/test_integration.py --asr-service-address HOST:PORT
```

### Test structure

| File | Type | Notes |
|------|------|-------|
| `test_cli.py` | Unit | CLI argument parsing and help text |
| `test_audio.py` | Unit | WAV loading and streaming; uses `wav_path` fixture (generated silence) |
| `test_channel.py` | Unit | gRPC channel creation |
| `test_version.py` | Unit | Version format validation |
| `test_integration.py` | Integration | Live ASR service; auto-skipped if `--asr-service-address` absent |
| `conftest.py` | Config | Registers `--asr-service-address`; provides `wav_path` fixture |

**Important:** The `asr_service_address` and `audio_wav` fixtures are defined inside `test_integration.py` itself — not in `conftest.py`. `audio_wav` expects `data/audio.wav` to exist; auto-skips if absent.

---

## Code Patterns

### `_generate_request_with_traceback` decorator

Defined in `__init__.py`. gRPC's C runtime silently swallows Python exceptions raised inside generator functions passed to a stub — they surface as `StatusCode.UNKNOWN "Exception iterating requests!"` with no traceback. This decorator catches exceptions, prints the traceback via `traceback.print_exc()`, then re-raises. Apply it to every generator function that feeds a gRPC stub.

Usage pattern (from `v1.py` and `dictation.py`):

```python
from itertools import chain

@_generate_request_with_traceback
def _generate_config_request(...) -> Iterator[...]:
    yield ConfigRequest(...)

@_generate_request_with_traceback
def _generate_data_requests(audio_stream, ...) -> Iterator[...]:
    for chunk in audio_stream:
        yield DataRequest(audio=chunk)

responses = stub.StreamingRecognize(
    chain(_generate_config_request(...), _generate_data_requests(audio_stream, ...)),
    metadata=...,
    timeout=...,
)
```

### TLS / channel creation

`create_grpc_channel_credentials` takes **bytes**, not file paths:

```python
# Insecure
with create_grpc_channel("host:port") as channel: ...

# One-way TLS (system root CAs)
creds = create_grpc_channel_credentials()
with create_grpc_channel("host:port", credentials=creds) as channel: ...

# mTLS
creds = create_grpc_channel_credentials(
    tls_certificate_chain=Path("client.crt").read_bytes(),
    tls_private_key=Path("client.key").read_bytes(),
    tls_root_certificates=Path("ca.crt").read_bytes(),
)
```

### Audio classes

- `AudioFile` — reads a WAV file via `pydub`, validates mono 16-bit PCM. Raises `AudioFileError` for format errors.
- `AudioFileStream(AudioStream)` — iterates `AudioFile` in chunks. `chunk_duration_ms` optional; omitting it sends the whole file as one chunk.
- `MicrophoneStream(AudioStream)` — PyAudio-based live capture. **Not a context manager** — cleanup via `__del__`. Requires `--audio-stream-chunk-duration`.

**Constraint:** `--audio-stream-chunk-duration` is required when `--audio-mic` is used. Enforced by a post-parse check in `parse_args()` — not by argparse itself.

### CLI argument validation

Custom argparse validators are local functions inside `parse_args()` in `__main__.py`: `assure_int()`, `positive_int()`, `unsigned_int()`, `non_empty_str()`. The `Once` action (also local) prevents an argument from being specified more than once. Use these patterns when adding new arguments.

### `build_additional_config_specs_dict` — key name transformation

Transforms kwarg names into server config keys:
- `__` (double underscore) → `.` (dot)
- `_` (single underscore) → `-` (hyphen)

Example: `decoder__beam_size` → `decoder.beam-size`.

**Convention for new tuning args:**
- CLI flag: dotted notation with hyphens — `--decoder.new-param`
- `dest`: double underscores for dots, single underscores for hyphens — `dest="decoder__new_param"`

Args whose value equals `"NA"` are excluded (that is the no-op default for optional `str` args). **Exception:** `--max-hypotheses-for-softmax` always forwarded (`default=10`, `type=unsigned_int`).

**Known inconsistency:** `--decoder.beam-threshold` has `dest="decoder__beam_size_threshold"` (spurious "size" — acknowledged by a `TODO`). The kwarg passed to the builder is correct. Do not use this `dest` as a naming template.

### `grpc.RpcError` exits 0

`main()` catches `grpc.RpcError`, prints it, and returns normally — process exits 0. **Do not write tests that assert `returncode != 0` to detect recognition failures.** Inspect stdout/stderr instead.

---

## Code Style

The codebase was written to these standards (even though pre-commit is not configured in this public repo):

| Convention | Detail |
|-----------|--------|
| `ruff` | Rules `E,W,F,I,S,UP,B`; ignores `S101` (asserts ok), `S603`, `S607` |
| line length | **160** — not 88 or 79 |
| `mypy --strict` | Full strict; per-module relaxations in `pyproject.toml` |

**The critical number is 160 — not 88.** Existing modules have `ignore_errors = true` in `pyproject.toml` for pre-existing issues. `asr_client/__init__.py` is actively checked. Write new code with full strict mypy compliance; do not add new modules to the `ignore_errors` list.

---

## Common Tasks

### Add a new CLI flag
1. Add the argument inside `parse_args()` in `__main__.py` in the appropriate group.
2. Use an existing local validator or write one following the same pattern.
3. Pass the value into the request builder or config dict.
4. Add a unit test in `test_cli.py`.

### Add support for a new API version
1. Add `v2.py` following the pattern in `v1.py` — an `Asr` class with `streaming_recognize`.
2. Add the version string to `--api-version` choices in `__main__.py`.
3. Add `elif args.api_version == "v2":` in the dispatch inside `main()` (before `else: raise AssertionError`).
4. Add integration tests in `test_integration.py`.

### Bump the version
1. Edit `asr_client/VERSION.py` (`__version__` string).
2. Update `CHANGELOG.md`.
3. `pyproject.toml` reads the version dynamically — do not edit it for version bumps.
