**Table of contents**

- [Overview](#overview)
- [Setup](#setup)
  - [Requirements](#requirements)
  - [Manual submodule update](#manual-submodule-update)
- [Install](#install)
  - [Using the provided script](#using-the-provided-script)
  - [Manual installation](#manual-installation)
- [Usage](#usage)
  - [ASR Client](#asr-client)

# ASR Client (Python)

The gRPC Python client for Techmo ASR Service.

## Overview

For project details, its structure, and functionality, head to [the documentation](doc/DOCUMENTATION.md).

## Setup

The project can be used as-is and does not require any additional setup.

*For basic development use, consider convenient `./setup.sh`.*

### Requirements

- [Python](https://www.python.org/) >=3.8
- [uv](https://docs.astral.sh/uv/) (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [PortAudio](https://files.portaudio.com/) 19.6.0 (required by the [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) Python package)

### Manual submodule update

It is the duty of the build configuration to clone all the necessary submodules. However, it sometimes fails, for example, when building a Docker image from an uninitialized repository. In that case, the solution is to download the missing dependencies manually.

Example:

```sh
git submodule update --init --depth 1 submodules/asr-api-python
```

Do not forget about the submodules of the submodules. Eventually, use the `--recursive` flag.

## Install

### Using the provided script

```sh
./install.sh
```

Creates a `.venv` virtualenv with [uv](https://docs.astral.sh/uv/) and installs the package with its dependencies.

### Manual installation

```sh
uv venv .venv
source .venv/bin/activate
uv pip install .
```

If installation fails, [the troubleshooting section of the documentation](doc/DOCUMENTATION.md#troubleshooting) may be helpful.

## Usage

### ASR Client

Performs speech recognition on an ASR Service instance.

```
asr_client [-h, --help] [-v, --version] [OPTIONS]... [-s, ]--service-address ADDRESS [-m, ]--audio-mic --audio-stream-chunk-duration ARG
asr_client [-h, --help] [-v, --version] [OPTIONS]... [-s, ]--service-address ADDRESS [-a, ]--audio-paths PATH...
```

Examples:

- perform speech recognition on an audio stream coming from a file

```sh
python -m asr_client -s 0.0.0.0:30384 -a ./audio.wav
```

- perform speech recognition on an audio stream coming from a microphone in 200-milliseconds chunks

```sh
python -m asr_client -s 0.0.0.0:30384 -m --audio-stream-chunk-duration 200
```

- perform speech recognition on an audio stream coming from a file on a zipformer model named `my_zipformer_model` with *decoder.criterion-type* set to S2S and *extractor.sampling-frequency* set to 16000:

```sh
python -m asr_client -s 0.0.0.0:30384 -a ./audio.wav --speech-model my_zipformer_model --decoder.criterion-type S2S --extractor.sampling-frequency 16000
```

- prepend 150 ms of silence to the audio before sending (useful when speech starts immediately at the beginning of the file and the voice activity detector needs a moment to prime):

```sh
python -m asr_client -s 0.0.0.0:30384 -a ./audio.wav --audio-prepend-silence 150
```

- append 300 ms of trailing silence (useful to ensure the detector finalises the last utterance):

```sh
python -m asr_client -s 0.0.0.0:30384 -a ./audio.wav --audio-append-silence 300
```

*For some more usage scenarios, head to [the documentation](doc/DOCUMENTATION.md#examples).*
