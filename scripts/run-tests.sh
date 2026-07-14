#!/usr/bin/env bash
set -euo pipefail

echo "=== entirius-tests ==="

# Install test package in editable mode
pip install --quiet -e /tests

# Wait for API to be ready
bash /tests/scripts/wait-for-api.sh

# Run behave with any extra arguments passed to the container
echo "Running tests..."
exec behave "$@"
