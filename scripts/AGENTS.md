# Scripts Guide

## Purpose

This directory contains OS-specific wrappers for starting and stopping the Docker stack.

## Files

- `start-mac.sh`: Start stack on macOS.
- `stop-mac.sh`: Stop stack on macOS.
- `start-linux.sh`: Start stack on Linux.
- `stop-linux.sh`: Stop stack on Linux.
- `start-windows.bat`: Start stack on Windows.
- `stop-windows.bat`: Stop stack on Windows.

## Behavior

- Start scripts run `docker compose up --build -d` from repo root.
- Stop scripts run `docker compose down` from repo root.

## Notes

- Shell scripts use strict mode (`set -euo pipefail`).
- Keep scripts thin wrappers; orchestration logic should remain in Compose config.