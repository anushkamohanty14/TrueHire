#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f ".env" ]; then
    echo "ERROR: .env not found."
    exit 1
fi

echo "Starting CogniHire..."
echo "API + Frontend: http://localhost:8000"
python -m uvicorn apps.api.src.main:app --reload --host 0.0.0.0 --port 8000
