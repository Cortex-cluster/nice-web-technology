#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_DIR="$ROOT_DIR/python_backend"
VENV_DIR="$ROOT_DIR/.venv"

if [[ ! -d "$PYTHON_DIR" ]]; then
  echo "Error: python_backend directory not found."
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Error: Python virtual environment not found."
  echo "Run ./install_dependencies.sh first."
  exit 1
fi

echo "Starting Python backend..."
cd "$PYTHON_DIR"
"$VENV_DIR/bin/python" main.py
