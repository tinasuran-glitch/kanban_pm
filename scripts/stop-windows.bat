@echo off
setlocal

cd /d "%~dp0\.."
docker compose down

if errorlevel 1 (
  echo Failed to stop stack.
  exit /b 1
)

echo Stack stopped.
