@echo off
setlocal

cd /d "%~dp0\.."
if exist "backend\data\pm.db" del /f /q "backend\data\pm.db"
docker compose up --build -d

if errorlevel 1 (
  echo Failed to start stack.
  exit /b 1
)

echo Stack started. Open http://localhost:8000
