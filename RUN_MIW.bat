@echo off
setlocal
cd /d "%~dp0"
python -I -B ./tools/miw.py gui --directory ./evidence/qualification/demo
if errorlevel 1 (
  echo.
  echo The viewer could not open. Read the diagnostic above. No fallback GUI was selected.
  pause
)
