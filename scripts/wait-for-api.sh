#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_BASE_URL:-http://volkanos:8000}"
TIMEOUT="${WAIT_TIMEOUT:-120}"

echo "Waiting for API at ${API_URL} (timeout: ${TIMEOUT}s)..."

elapsed=0
while [ "$elapsed" -lt "$TIMEOUT" ]; do
    if python3 -c "
import urllib.request, sys
try:
    r = urllib.request.urlopen('${API_URL}/health/', timeout=5)
    sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
" 2>/dev/null; then
        echo "API is ready."
        exit 0
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    echo "  ... waiting (${elapsed}s)"
done

echo "ERROR: API not ready after ${TIMEOUT}s"
exit 1
