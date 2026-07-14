#!/usr/bin/env bash
# Generate behave.ini from entirius-docker .env for standalone usage.
# Usage: ./scripts/generate-behave-ini.sh [path-to-env-file]
set -euo pipefail

ENV_FILE="${1:-.env}"

if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

cat > behave.ini << EOF
[behave]
paths = features
junit = true
junit_directory = reports
show_timings = true
format = pretty

[behave.userdata]
api_base_url = http://localhost:${BACKEND_PORT:-8000}
api_version = 1
test_package_path = ${TEST_PACKAGE_PATH:-../entirius-test-package}/package
admin_username = ${ADMIN_USERNAME:-admin}
admin_password = ${ADMIN_PASSWORD:-admin123}
test_username = ${TEST_USERNAME:-testuser}
test_password = ${TEST_PASSWORD:-testuser123}
channels = ${TEST_CHANNELS:-default-europe,default-local}
primary_channel = ${TEST_PRIMARY_CHANNEL:-${DEFAULT_CHANNEL:-default-europe}}
EOF

echo "Generated behave.ini"
