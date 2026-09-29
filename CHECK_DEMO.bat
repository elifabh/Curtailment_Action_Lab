@echo off
setlocal
cd /d "%~dp0"
echo Checking local demo and configured Azure access. Azure check may consume quota.
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\check_demo.py --azure
) else (
  py -3 scripts\check_demo.py --azure
)
pause
