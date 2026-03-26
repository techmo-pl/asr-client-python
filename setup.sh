#!/bin/bash
#
# usage: ./setup.sh
#
# Run once after cloning: initialises git submodules.

set -euo pipefail

git submodule sync --recursive
git submodule update --init --recursive
