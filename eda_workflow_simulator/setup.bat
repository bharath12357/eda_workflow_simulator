@echo off
REM One-time setup: creates a virtual environment (optional, no packages needed).
cd /d "%~dp0"
py -3 --version || (echo Python 3 not found. Install from https://www.python.org/downloads/ and tick "Add python.exe to PATH". & exit /b 1)
py -3 -m venv .venv || exit /b 1
echo.
echo Virtual environment created in .venv
echo Activate it in PowerShell with:  .venv\Scripts\Activate.ps1
echo Activate it in Command Prompt:   .venv\Scripts\activate.bat
