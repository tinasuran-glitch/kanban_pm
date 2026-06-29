#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
	if [[ -x "/Applications/Docker.app/Contents/Resources/bin/docker" ]]; then
		export PATH="/Applications/Docker.app/Contents/Resources/bin:${PATH}"
	fi
fi

if ! command -v docker >/dev/null 2>&1; then
	echo "Docker CLI not found. Install Docker Desktop and reopen Terminal."
	exit 127
fi

cd "${ROOT_DIR}"
rm -f "${ROOT_DIR}/backend/data/pm.db"
docker compose up --build -d

echo "Stack started. Open http://localhost:8000"
