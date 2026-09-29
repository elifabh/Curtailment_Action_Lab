@echo off
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Installation complete. Double-click START_LOCAL.bat.
pause
exit /b 0
:failed
echo Installation failed. Install Python 3.12 and read START_HERE_TR.md.
pause
exit /b 1
