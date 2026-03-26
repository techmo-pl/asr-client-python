#!/bin/bash
#
# usage: ./install.sh [VENV_PATH]
#
# VENV_PATH: Optional path for the virtual environment (default: ./.venv).
#
# Creates a virtualenv with uv and installs the package with test dependencies.

set -euo pipefail

# --- prerequisite checks --------------------------------------------------
# pyaudio requires a C compiler, Python headers, and PortAudio headers.
# Check all three up front so the user gets a clear message instead of a
# cryptic C compiler error buried inside the pip build log.
_prereq_ok=1

if ! command -v uv > /dev/null 2>&1; then
    echo "error: 'uv' not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    _prereq_ok=0
fi

if ! command -v gcc > /dev/null 2>&1; then
    echo "error: C compiler (gcc) not found; required to build pyaudio." >&2
    echo "       Fix: sudo apt install build-essential" >&2
    _prereq_ok=0
fi

_python_include="$(python3 -c 'import sysconfig; print(sysconfig.get_path("include"))' 2> /dev/null)"
if [ ! -f "${_python_include}/Python.h" ]; then
    echo "error: Python header files not found; required to build pyaudio." >&2
    echo "       Fix: sudo apt install python3-dev" >&2
    _prereq_ok=0
fi

if [ ! -f /usr/include/portaudio.h ] && [ ! -f /usr/local/include/portaudio.h ]; then
    echo "error: PortAudio headers not found; required to build pyaudio." >&2
    echo "       Fix: sudo apt install portaudio19-dev" >&2
    _prereq_ok=0
fi

if [ "${_prereq_ok}" -eq 0 ]; then
    echo "" >&2
    echo "Install all missing system packages at once:" >&2
    echo "  sudo apt install python3-dev portaudio19-dev build-essential" >&2
    exit 1
fi
# --------------------------------------------------------------------------

VENV_PATH="${1:-.venv}"

if [ ! -d "${VENV_PATH}" ]; then
    uv venv "${VENV_PATH}"
fi

# shellcheck disable=SC1091
source "${VENV_PATH}/bin/activate"
uv pip install -e ".[test]"
