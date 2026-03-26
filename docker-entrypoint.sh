#!/bin/bash

set -euo pipefail

if [ "$#" -eq 0 ] || [ "${1:0:1}" = '-' ]; then
    set -- python asr_client "$@"
fi

exec "$@"
