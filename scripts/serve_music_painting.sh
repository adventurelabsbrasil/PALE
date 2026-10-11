#!/bin/sh
set -eu
exec python3 "$(dirname "$0")/music_painting_server.py" "${1:-8007}"
