# Changelog of ASR Client (Python)


## [1.6.0] - 2026-03-24

### Added

- `asr_client/__main__.py`: `--audio-prepend-silence <ms>` option: prepends zero-filled PCM silence to the audio stream before sending to the ASR service; works for both `--audio-paths` and `--audio-mic`; useful for priming the detector when the utterance starts immediately at the beginning of the audio.
- `asr_client/__main__.py`: `--audio-append-silence <ms>` option: appends zero-filled PCM silence to the audio stream; works for both `--audio-paths` and `--audio-mic`; useful for ensuring the detector has enough trailing silence to finalise the last utterance.
