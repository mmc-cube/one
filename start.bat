@echo off
chcp 65001 >nul
title Baili Electronics

echo ============================================
echo   Baili Electronics - MCU Project Customization & Development Platform
echo ============================================
echo.

cd /d "%~dp0"

:: Check if .env exists
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo Copy .env.example to .env and fill in your API key.
    echo.
)

echo [INFO] Starting backend server...
echo [INFO] Address: http://127.0.0.1:43210
echo [INFO] Press Ctrl+C to stop.
echo.

python backend\server.py

pause
