#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

uv tool install --force --editable . --with pyyaml

echo
echo "Installed. Verify with: outline --help"
