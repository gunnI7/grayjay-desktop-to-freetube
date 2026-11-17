#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/grayjay_to_freetube.py"

if [ ! -f "$SCRIPT" ]; then
    echo "Error: grayjay_to_freetube.py was not found next to this script." >&2
    exit 1
fi

if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "Error: Python 3 is required. Install Python 3 and try again." >&2
    exit 1
fi

"$PYTHON_CMD" "$SCRIPT" "$@"
