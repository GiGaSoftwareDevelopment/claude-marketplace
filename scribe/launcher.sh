#!/usr/bin/env bash
# scribe MCP launcher.
#
# Cowork/Code calls this script as the MCP `command`. We use it to bootstrap
# a local Python venv on first run (so the user doesn't have to pre-install
# the `mcp` package globally), then exec the actual server.
#
# Idempotent: subsequent launches reuse the venv. Self-healing: if the venv
# is missing or its interpreter doesn't work (stale shebang from a moved
# install), we recreate it.

set -euo pipefail

PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$PLUGIN_DIR/.venv"
SERVER="$PLUGIN_DIR/server.py"

if ! command -v python3 >/dev/null 2>&1; then
  echo "scribe: python3 not found on PATH; install Xcode Command Line Tools (xcode-select --install) and retry." >&2
  exit 1
fi

# Detect a broken/stale venv (e.g. shebangs pointing at a moved install).
if [[ -d "$VENV" ]] && ! "$VENV/bin/python3" --version >/dev/null 2>&1; then
  rm -rf "$VENV"
fi

if [[ ! -d "$VENV" ]]; then
  echo "scribe: setting up local Python venv (one-time)..." >&2
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet "mcp>=1.0"
fi

# Sanity check: mcp must be importable.
if ! "$VENV/bin/python3" -c "import mcp" >/dev/null 2>&1; then
  echo "scribe: mcp package is missing from the venv. Re-running pip install..." >&2
  "$VENV/bin/pip" install --quiet "mcp>=1.0"
fi

exec "$VENV/bin/python3" "$SERVER" "$@"
