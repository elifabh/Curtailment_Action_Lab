@echo off
setlocal
cd /d "%~dp0"
echo Installing the optional Irish calculation engine into the Python used by START_LOCAL.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m pip install -r requirements-irish-extension.txt
) else (
  py -3 -m pip install -r requirements-irish-extension.txt
)
if errorlevel 1 (
  echo Installation failed. The recorded demo remains available.
  pause
  exit /b 1
)
echo Installation complete. Close any running local server, then run START_LOCAL.bat.
pause
