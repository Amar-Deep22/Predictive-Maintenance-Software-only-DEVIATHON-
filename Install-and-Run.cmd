@echo off
setlocal
cd /d "%~dp0"
title AXIOM - Install and run
if not exist package-lock.json (
  echo Extract the entire project ZIP before running this file.
  pause
  exit /b 1
)
call :checknode
if errorlevel 1 (
  echo Node.js 22.12 or newer is needed. Installing the official Node.js LTS package using Windows Package Manager...
  where winget.exe >nul 2>&1
  if errorlevel 1 (
    echo Windows Package Manager was not found. Install Node.js LTS from https://nodejs.org and run this file again.
    pause
    exit /b 1
  )
  winget install --id OpenJS.NodeJS.LTS --exact --source winget --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo Node.js installation did not complete. Resolve the installer message, then run this file again.
    pause
    exit /b 1
  )
)
rem Include the standard Node installer location in this process only.
set "PATH=%ProgramFiles%\nodejs;%PATH%"
call :checknode
if errorlevel 1 (
  echo A compatible Node.js installation is not available in this terminal.
  echo Close this window and run this file again after Node.js installation completes.
  pause
  exit /b 1
)
where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo npm was not found. Repair the Node.js LTS installation, then retry.
  pause
  exit /b 1
)
echo Installing the exact dependencies from package-lock.json...
call npm.cmd ci --no-audit --no-fund
if errorlevel 1 goto :failed
echo Building and checking the app...
call npm.cmd run build
if errorlevel 1 goto :failed
echo Preparing the FD001 model backend...
python --version >nul 2>&1
if errorlevel 1 (
  echo Install Python 3.11, 3.12 or 3.13 and enable Add Python to PATH, then retry.
  goto :failed
)
if not exist .venv\Scripts\python.exe python -m venv .venv
if errorlevel 1 goto :failed
call .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 goto :failed
echo Open http://127.0.0.1:8767 after Application startup complete appears.
echo Keep this window open while using the portal.
call .venv\Scripts\python.exe run.py
if errorlevel 1 goto :failed
exit /b 0

:checknode
node -e "const [a,b]=process.versions.node.split('.').map(Number);process.exit(a>22||(a===22&&b>=12)?0:1)" >nul 2>&1
exit /b %errorlevel%

:failed
echo Setup stopped because the command above failed. Keep its error message for troubleshooting.
pause
exit /b 1
