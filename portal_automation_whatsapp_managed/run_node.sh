#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_DIR="$ROOT_DIR/node_app"

if [[ ! -d "$NODE_DIR" ]]; then
  echo "Error: node_app directory not found."
  exit 1
fi

if [[ ! -d "$NODE_DIR/node_modules" ]]; then
  echo "Error: Node dependencies not found."
  echo "Run ./install_dependencies.sh first."
  exit 1
fi

echo "Starting Node app..."
cd "$NODE_DIR"
npm start
