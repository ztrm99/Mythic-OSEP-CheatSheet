#!/usr/bin/env bash
set -euo pipefail

URL=${1:-}
PORT_HTTP=${2:-"8081"}
PORT_MYTHIC=${3:-"80"}
MODE=${4:-"both"}

TEMPLATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$TEMPLATE_DIR/mythicConfig/venv"
REQ_FILE="$TEMPLATE_DIR/mythicConfig/requirements.txt"

if [ -z "$URL" ]; then
  echo "Usage: $0 <URL> [PORT_HTTP] [PORT_MYTHIC] [apollo|poseidon|both]"
  exit 1
fi

if [ -z "${MYTHIC_PASSWORD:-}" ]; then
  echo "Set MYTHIC_PASSWORD before running this script."
  exit 1
fi


# Mythic
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR" || { echo "Failed to create venv at $VENV_DIR"; exit 1; }
fi

source "$VENV_DIR/bin/activate" || { echo "Failed to activate venv"; exit 2; }

python3 -m pip install --upgrade pip >/dev/null 2>&1

if [ -f "$REQ_FILE" ]; then
  python3 -m pip install -r "$REQ_FILE" || { echo "Failed to install requirements from $REQ_FILE"; exit 3; }
else
  echo "Warning: requirements.txt not found at $REQ_FILE"
fi

mkdir -p payloads
python3 "$TEMPLATE_DIR/mythicConfig/generatePayloads.py" \
  "$URL" "$PORT_MYTHIC" "$MODE" --output-dir "$PWD/payloads"

# AuxConfigs files - Powershell, etc
bash "$TEMPLATE_DIR/auxConfig/loadShell.sh" "$URL" "$PORT_HTTP"


# Copy Utils folder
cp -R "$TEMPLATE_DIR/utils" .
