# Documentation of **ASR** Client (Python)

## Usage

### Examples

#### Microphone

To use a microphone as the audio source instead of an audio file, specify the `--audio-mic` option and set the chunk size for the audio stream.

Example:

```bash
python -m asr_client -s 0.0.0.0:30384 -m --audio-stream-chunk-duration 200
```

In such a configuration, the application sends audio indefinitely in 200-milliseconds chunks unless it receives a termination signal, e.g., by pressing `Ctrl+C`.

To automatically stop recognition after the end of an utterance is detected, specify the `--enable-single-utterance` option additionally.

Example:

```bash
python -m asr_client -s 0.0.0.0:30384 -m --audio-stream-chunk-duration 200 --enable-single-utterance
```

**The choice of an input audio device depends on the current system settings.** If no results are received, it is probably caused be a disabled, muted or incorrect input audio device selected.

#### Multiple audio files

It is possible to pass multiple audio files to the application at once. They get sent one by one.

Example:

```bash
python -m asr_client -s 0.0.0.0:30384 -a ./audio/*.wav
```

However, with this approach the service treats each audio file as coming from a separate sender. That should not alter speech recognition results but may influence the output that depends on the quantity of incoming data, e.g., age or gender recognition. To get around that, the service's session caching feature (if enabled) may be used by specifying a custom freeform session ID with the `--session-id` option.

Example:

```bash,
python -m asr_client -s 0.0.0.0:30384 -a ./audio/*.wav --session-id "$(whoami)'s session"
```

Now, even if the audio files are sent sequentially, the service treats them as parts of a single request. The previous result is continuously updated with every new portion of data from another request.

#### Prepending silence

Some ASR service configurations use a voice activity detector (VAD) that needs a short period of silence at the start of the audio to initialise before speech begins. The `--audio-prepend-silence` option prepends the given number of milliseconds of zero-filled PCM silence to the audio stream on the client side before it is sent to the service.

Example — prepend 150 ms of silence to a file:

```bash
python -m asr_client -s 0.0.0.0:30384 -a ./audio.wav --audio-prepend-silence 150
```

Example — prepend 150 ms of silence when streaming from a microphone:

```bash
python -m asr_client -s 0.0.0.0:30384 -m --audio-stream-chunk-duration 200 --audio-prepend-silence 150
```

The silence is computed in whole PCM samples to guarantee byte alignment for any sample rate. For microphone streams the duration is rounded up to the nearest chunk boundary (so the actual prepended silence may be slightly longer than requested, by at most one chunk duration).

#### Appending silence

Some ASR service configurations require a short period of trailing silence after speech ends to ensure the voice activity detector finalises recognition of the last utterance. The `--audio-append-silence` option appends the given number of milliseconds of zero-filled PCM silence to the audio stream on the client side.

Example — append 300 ms of silence to a file:

```bash
python -m asr_client -s 0.0.0.0:30384 -a ./audio.wav --audio-append-silence 300
```

**Note:** `--audio-append-silence` only takes effect for file streams (`--audio-paths`). When streaming from a microphone (`--audio-mic`), the flag is accepted but the trailing silence is not sent, because the gRPC stream is cancelled on `Ctrl+C` before the silence chunks are yielded.

Both options may be combined:

```bash
python -m asr_client -s 0.0.0.0:30384 -a ./audio.wav --audio-prepend-silence 150 --audio-append-silence 300
```

The same alignment and rounding rules as for `--audio-prepend-silence` apply.

#### Real-time recognition of audio files

It is possible to simulate real-time recognition of existing audio data by sending chunks of it at the same intervals.

Example:

```bash
python -m asr_client -s 0.0.0.0:30384 -a ./audio.wav --audio-stream-chunk-duration 200 --audio-stream-chunk-interval 200
```

#### "MRCPv2 in gRPC" ambiguity

As stated, this package provides a client that uses the gRPC communication protocol that has nothing in common with [MRCPv2](https://datatracker.ietf.org/doc/rfc6787/). The implemented APIs are designed to serve some functionalities inspired by MRCPv2 however. Thereupon, there are some CLI parameters starting with the `--mrcp-` prefix. These are so named to indicate the analogy but are susceptible to changes in the unspecified future.

## Troubleshooting

### Install

#### Missing uv

`./install.sh` requires [uv](https://docs.astral.sh/uv/). If `uv` is not found, install it with the standalone installer:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then open a new shell (or run `source ~/.local/bin/env`) so that `~/.local/bin` is on `PATH`.

#### Missing Python include

If installation fails with a message similar to this one

```
src/_portaudiomodule.c:28:10: fatal error: Python.h: No such file or directory
      #include "Python.h"
              ^~~~~~~~~~
    compilation terminated.
    error: command '/usr/bin/x86_64-linux-gnu-gcc' failed with exit code 1
```

it means that the Python library is missing.

For the apt package manager (Debian, Ubuntu, etc.), run:

```bash
apt install python3-dev
```

#### Missing PortAudio include

If installation fails with a message similar to this one:

```
src/_portaudiomodule.c:29:10: fatal error: portaudio.h: No such file or directory
      #include "portaudio.h"
              ^~~~~~~~~~~~~
    compilation terminated.
    error: command 'x86_64-linux-gnu-gcc' failed with exit status 1
```

it means that the PortAudio library is missing.

For the apt package manager (Debian, Ubuntu, etc.), run:

```bash
apt install portaudio19-dev
```

#### Missing GCC

If installation fails with a message similar to this one

```
Building wheels for collected packages: pyaudio
  Building wheel for pyaudio (pyproject.toml): started
  Building wheel for pyaudio (pyproject.toml): finished with status 'error'
  error: subprocess-exited-with-error

  × Building wheel for pyaudio (pyproject.toml) did not run successfully.
  │ exit code: 1
  ╰─> [14 lines of output]
      running bdist_wheel
      running build
      running build_py
      creating build
      creating build/lib.linux-x86_64-cpython-38
      creating build/lib.linux-x86_64-cpython-38/pyaudio
      copying src/pyaudio/__init__.py -> build/lib.linux-x86_64-cpython-38/pyaudio
      running build_ext
      building 'pyaudio._portaudio' extension
      creating build/temp.linux-x86_64-cpython-38
      creating build/temp.linux-x86_64-cpython-38/src
      creating build/temp.linux-x86_64-cpython-38/src/pyaudio
      gcc -Wno-unused-result -Wsign-compare -DNDEBUG -g -fwrapv -O3 -Wall -fPIC -I/usr/local/include -I/usr/include -I/usr/local/include/python3.8 -c src/pyaudio/device_api.c -o build/temp.linux-x86_64-cpython-38/src/pyaudio/device_api.o
      error: command 'gcc' failed: No such file or directory
      [end of output]

  note: This error originates from a subprocess, and is likely not a problem with pip.
  ERROR: Failed building wheel for pyaudio
Failed to build pyaudio
ERROR: Could not build wheels for pyaudio, which is required to install pyproject.toml-based projects
```

it means that GCC (the GNU Compiler Collection) is missing.

For the apt package manager (Debian, Ubuntu, etc.), run:

```bash
apt install build-essential
```

### Usage

#### ALSA warnings

If the following or a similar warnings appear:

```
ALSA lib pcm_dsnoop.c:618:(snd_pcm_dsnoop_open) unable to open slave
ALSA lib pcm.c:2495:(snd_pcm_open_noupdate) Unknown PCM cards.pcm.rear
ALSA lib pcm.c:2495:(snd_pcm_open_noupdate) Unknown PCM cards.pcm.center_lfe
ALSA lib pcm.c:2495:(snd_pcm_open_noupdate) Unknown PCM cards.pcm.side
```

it is caused by the ALSA (Advanced Linux Sound Architecture) configuration. It is not a serious problem and can be ignored as long as the microphone input works. Eventually, it may be resolved by modifying the configuration.

Locate the `/usr/share/alsa/alsa.conf` file and comment out all the lines that define audio interfaces marked as "unknown" using `#`. This operation requires root privileges. Remember to make a backup of the original file.

Example:

```
[...]
# pcm.rear cards.pcm.rear
# pcm.center_lfe cards.pcm.center_lfe
# pcm.side cards.pcm.side
[...]
```

#### FFmpeg warnings

If the following or a similar warning appears:

```
RuntimeWarning: Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
```

it is caused by the FFmpeg framework not being installed. It is not a serious problem and can be ignored as long as the application works only with WAV files. Eventually, it may be resolved by installing FFmpeg.

For the apt package manager (Debian, Ubuntu, etc.), run:

```bash
apt install ffmpeg
```

#### Non-OK gRPC status

##### _Exception iterating requests!_ (**StatusCode.UNKNOWN**)

If the following or a similar gRPC status appears:

```
<_MultiThreadedRendezvous of RPC that terminated with:
        status = StatusCode.UNKNOWN
        details = "Exception iterating requests!"
        debug_error_string = "None"
>
```

it means that the gRPC library failed to build a stream of request. Usually, one of its messages is ill-formed, and that happens when an invalid argument is assigned to a parameter of the message or its invalid parameter is referenced. If the code has not been modified in any way but the error occurs, it is a bug, and it means that the invalid parameter is not handled ahead of time by the client application itself. In such a case, feel free to create an issue to report the bug.

##### _Received message larger than max [...]_ (**StatusCode.RESOURCE_EXHAUSTED**)

If the following or a similar gRPC status appears:

```
<_MultiThreadedRendezvous of RPC that terminated with:
        status = StatusCode.RESOURCE_EXHAUSTED
        details = "Received message larger than max (8317787 vs. 4194304)"
        debug_error_string = "UNKNOWN:Error received from peer ipv4:127.0.0.1:30384 {created_time:"2023-11-29T08:23:29.269587674+01:00", grpc_status:8, grpc_message:"Received message larger than max (8317787 vs. 4194304)"}"
>
```

it means that the client tried to send a message larger than accepted by a service. By default, the gRPC library limits the size of incoming messages to 4 MB. If an audio file is too big to be sent at once, a most straightforward solution is to set the `--audio-stream-chunk-size` option to stream it in smaller chunks.
