# Run Locally (Parts 2 and 3)

## Start

From repo root:

- macOS: `./scripts/start-mac.sh`
- Linux: `./scripts/start-linux.sh`
- Windows: `scripts\\start-windows.bat`

## Verify

- App UI: `http://localhost:8000`
- API health: `http://localhost:8000/api/health`

Expected health response:

```json
{"status":"ok","service":"backend"}
```

## Stop

From repo root:

- macOS: `./scripts/stop-mac.sh`
- Linux: `./scripts/stop-linux.sh`
- Windows: `scripts\\stop-windows.bat`

## Notes

- Gateway (`nginx`) routes `/` to Next.js and `/api/*` to FastAPI.
- `docker compose up --build -d` is wrapped by start scripts.
