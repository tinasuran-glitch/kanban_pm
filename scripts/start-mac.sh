#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"
rm -f "${ROOT_DIR}/backend/data/pm.db"
docker compose up --build -d

echo "Stack started. Open http://localhost:8000"
