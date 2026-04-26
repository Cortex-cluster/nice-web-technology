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

echo "Installing Python dependencies..."

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is not installed."
  exit 1
fi

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$PYTHON_DIR/requirements.txt"

echo "Installing Node.js dependencies..."

if ! command -v npm >/dev/null 2>&1; then
  echo "Error: npm is not installed."
  exit 1
fi

npm install --prefix "$NODE_DIR"

echo
echo "Done."
echo "Python virtual environment: $VENV_DIR"
echo "Node dependencies installed in: $NODE_DIR/node_modules"
