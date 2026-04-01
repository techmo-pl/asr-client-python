# AGENTS.md — asr-client-python

Guidance for AI coding agents working in this repository.

---

## What this repo is

A gRPC CLI client and Python library for the Techmo ASR (Automatic Speech Recognition) Service. Entry point: `asr_client.__main__:main` (installed as `asr-client`). The gRPC stubs come from `techmo-asr-api` (fetched from `github.com/techmo-pl/asr-api-python` at install time) and are generated at install time — they are never committed.

---

## Setup

Run once after cloning:

```bash
./install.sh  # create .venv and install package + test deps
```

`install.sh` requires system packages to build `pyaudio` — it will tell you exactly what's missing:

```bash
apt install python3-dev portaudio19-dev build-essential
```

If `from asr_api import ...` fails, re-run `./install.sh` (it fetches `techmo-asr-api` from GitHub automatically).

---

## Running tests

```bash
# Fast — no live service required
pytest tests/ -k "not integration"

# With coverage
pytest tests/ --cov=asr_client --cov-report=term-missing -k "not integration"

# Full matrix (Python 3.8–3.14), requires tox-uv
tox

# Single Python version
tox -e py311

# Integration tests — requires a live ASR service
pytest tests/test_integration.py --asr-service-address HOST:PORT
```

All tests except integration are self-contained. Integration tests auto-skip when `--asr-service-address` is absent.

---

## Package layout

```
asr_client/
├── __init__.py          # create_grpc_channel(), create_grpc_channel_credentials(),
│                        # _generate_request_with_traceback decorator
├── __main__.py          # CLI: argument parsing, TLS setup, streaming dispatch
├── audio_processing.py  # AudioFile, AudioFileStream, MicrophoneStream
├── v1.py                # v1 and v1p1 API (shared implementation, stub selected by arg)
├── dictation.py         # Legacy dictation API
└── VERSION.py           # __version__ string
```

The `asr_api` package (gRPC stubs) is installed as `techmo-asr-api @ git+https://github.com/techmo-pl/asr-api-python.git@1.1.4` — fetched from GitHub at install time, not from PyPI.

---

## Hard constraints

**Never commit generated files.** `*_pb2.py` and `*_pb2_grpc.py` are produced by `grpc_tools.protoc` at install time. They live in the submodule's build output, not in this repo.

**Do not add modules to `ignore_errors` in `pyproject.toml`.** All existing source modules have mypy errors suppressed (`ignore_errors = true`) as a legacy exception. New code must be written with full `mypy --strict` compliance.

**Do not remove the `warnings.catch_warnings()` block in `audio_processing.py`.** It suppresses a `SyntaxWarning` from `pydub` on Python 3.14. Removing it breaks the import on that version.

**Do not change gRPC metadata key names** without verifying server-side expectations:
- `v1` / `v1p1` API: session metadata key is `"session-id"` (hyphen)
- `dictation` API: session metadata key is `"session_id"` (underscore)

**`grpc.RpcError` exits 0.** `main()` catches it, prints it, and returns normally. Do not write tests that assert `returncode != 0` to detect recognition failures — check stdout/stderr content instead.

---

## Code style

| Rule | Value |
|------|-------|
| Line length | **160** (not 88 or 79) |
| Linter | `ruff` — rules `E,W,F,I,S,UP,B`; ignores `S101`, `S603`, `S607` |
| Type checking | `mypy --strict` |
| Shell scripts | `shellcheck` + `shfmt` (4-space indent) |

160 is the enforced line length. Standard PEP 8 limits do not apply here.

---

## Key patterns

### Generator → gRPC stub: always use `_generate_request_with_traceback`

gRPC's C runtime silently swallows exceptions raised inside generator functions passed to a stub. Without this decorator the failure surfaces only as `StatusCode.UNKNOWN "Exception iterating requests!"` with no traceback. Apply it to every generator that feeds a stub:

```python
from asr_client import _generate_request_with_traceback
from itertools import chain

@_generate_request_with_traceback
def _generate_config_request(...): yield ...

@_generate_request_with_traceback
def _generate_data_requests(audio_stream, ...): yield ...

responses = stub.StreamingRecognize(
    chain(_generate_config_request(...), _generate_data_requests(...)),
    metadata=...,
)
```

### API version dispatch

| `--api-version` | Module | Stub | Response key |
|----------------|--------|------|--------------|
| `v1p1` (default) | `v1.py` | `asr_api.v1p1.AsrStub` | `"result"` |
| `v1` | `v1.py` | `asr_api.v1.AsrStub` | `"result"` |
| `dictation` | `dictation.py` | `asr_api.dictation.SpeechStub` | `"results"` |

`v1` and `v1p1` share one implementation file; the stub is selected by the `api_patch_version` argument (`None` → v1, `1` → v1p1).

### Additional config key encoding

`build_additional_config_specs_dict()` transforms kwarg names to server keys:
- `__` → `.`  (double underscore → dot)
- `_` → `-`   (single underscore → hyphen)

New tuning CLI args must follow this convention: `--decoder.new-param` with `dest="decoder__new_param"`. Args with value `"NA"` are excluded. `--max-hypotheses-for-softmax` is always forwarded regardless.

### CLI argument validators

Defined as local functions inside `parse_args()`: `assure_int`, `positive_int`, `unsigned_int`, `non_empty_str`. The `Once` action prevents an argument from being repeated. Use these when adding new CLI arguments.

### gRPC 4 MB limit

The default max incoming message size is 4 MB. Sending a file larger than ~4 MB as a single chunk fails with `StatusCode.RESOURCE_EXHAUSTED`. Always use `--audio-stream-chunk-duration` for large files in tests and examples.

---

## Adding things

### New CLI flag
1. Add inside `parse_args()` in `__main__.py` using an existing validator or a new one following the same pattern.
2. Thread the value through to the request builder or config dict.
3. Add a test in `test_cli.py`.

### New API version
1. Add `v2.py` following the pattern in `v1.py`.
2. Add the version string to `--api-version` choices.
3. Add `elif args.api_version == "v2":` in the dispatch in `main()` before `else: raise AssertionError`.
4. Add integration tests in `test_integration.py`.

### Version bump
1. Edit `asr_client/VERSION.py`.
2. Update `CHANGELOG.md`.
3. Do not edit `pyproject.toml` — it reads the version dynamically from `VERSION.py`.

---

## Test layout

| File | What it tests |
|------|--------------|
| `test_cli.py` | Argument parsing, help text |
| `test_audio.py` | WAV loading, streaming (`wav_path` fixture generates silence) |
| `test_channel.py` | gRPC channel creation |
| `test_version.py` | Version string format |
| `test_integration.py` | Live ASR service (auto-skips without `--asr-service-address`) |
| `conftest.py` | Registers `--asr-service-address`; provides `wav_path` fixture |

`asr_service_address` and `audio_wav` fixtures are defined in `test_integration.py`, not `conftest.py`. `audio_wav` requires `data/audio.wav` and auto-skips if absent.
