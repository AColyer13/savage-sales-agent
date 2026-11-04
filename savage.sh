#!/usr/bin/env sh
# Savage Sales Agent launcher (macOS / Linux / Git Bash).
# First run: checks your computer and starts guided setup. After that: opens the agent.
# One-shot use still works after setup:  ./savage.sh -p "/objection ..."
cd "$(dirname "$0")" || exit 1
if [ "$#" -gt 0 ] && [ -f .savage_setup_done ]; then
  exec claude "$@"
fi
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "Python is not installed. Get it from https://www.python.org/downloads/ then run ./savage.sh again."
  exit 1
fi
exec "$PY" setup.py --launch
