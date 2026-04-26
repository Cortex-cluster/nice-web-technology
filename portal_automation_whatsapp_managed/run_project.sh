#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -d "$ROOT_DIR/python_backend" && -d "$ROOT_DIR/node_app" ]]; then
  PROJECT_DIR="$ROOT_DIR"
elif [[ -d "$ROOT_DIR/portal_automation_whatsapp_managed/python_backend" && -d "$ROOT_DIR/portal_automation_whatsapp_managed/node_app" ]]; then
  PROJECT_DIR="$ROOT_DIR/portal_automation_whatsapp_managed"
else
  echo "Error: Could not locate project directories."
  exit 1
fi

PYTHON_DIR="$PROJECT_DIR/python_backend"
NODE_DIR="$PROJECT_DIR/node_app"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_PID=""

cleanup() {
  if [[ -n "$PYTHON_PID" ]] && kill -0 "$PYTHON_PID" >/dev/null 2>&1; then
    echo
    echo "Stopping Python backend..."
    kill "$PYTHON_PID" >/dev/null 2>&1 || true
    wait "$PYTHON_PID" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Error: Python virtual environment not found."
  echo "Run ./install_dependencies.sh first."
  exit 1
fi

if [[ ! -d "$NODE_DIR/node_modules" ]]; then
  echo "Error: Node dependencies not found."
  echo "Run ./install_dependencies.sh first."
  exit 1
fi

echo "Starting Python backend..."
(
  cd "$PYTHON_DIR"
  "$VENV_DIR/bin/python" main.py
) &
PYTHON_PID=$!

echo "Starting Node app..."
cd "$NODE_DIR"
npm start
