@echo off
setlocal
cd /d "%~dp0"
title Digital Twin for Smart Farming - Setup

echo ============================================================
echo  DIGITAL TWIN FOR SMART FARMING - FIRST-TIME SETUP
echo ============================================================

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher was not found. Install Python 3.11 or 3.12 from https://www.python.org/downloads/windows/
  echo During installation, enable "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the Python virtual environment...
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 py -3.11 -m venv .venv 2>nul
  if errorlevel 1 py -m venv .venv
  if errorlevel 1 (
    echo Could not create the virtual environment. Install Python 3.11 or newer.
    pause
    exit /b 1
  )
)

call ".venv\Scripts\activate.bat"
python -c "import sys; print('Python', sys.version); raise SystemExit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo Python 3.11 or newer is required. Reinstall using Python 3.11 or 3.12.
  pause
  exit /b 1
)

echo Installing required Python packages. Internet access is required.
python -m pip install --upgrade pip
if errorlevel 1 goto :failed
python -m pip install -r requirements.txt
if errorlevel 1 goto :failed

if not exist ".env" (
  copy ".env.example" ".env" >nul
  echo Created .env with the local Docker MySQL defaults.
) else (
  echo Existing .env preserved.
)

echo.
echo Setup completed.
echo Next: run RUN_WINDOWS.bat. Docker Desktop is recommended for MySQL.
echo If you use an existing MySQL installation, edit .env first.
pause
exit /b 0

:failed
echo.
echo Package installation failed. Check your internet connection and Python version.
echo If a geospatial package failed to install, use Python 3.11 or 3.12 and retry setup.
pause
exit /b 1
