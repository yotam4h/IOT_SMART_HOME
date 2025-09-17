#!/usr/bin/env bash
set -euo pipefail

# Development helper: clear log files before starting the full stack.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs"

if [[ -d "$LOG_DIR" ]]; then
  find "$LOG_DIR" -type f -name '*.log' -exec truncate -s 0 {} +
fi

exec "$ROOT_DIR/start_emulators.sh"
