@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m pip install -r requirements.txt
  goto :done
)
python -m pip install -r requirements.txt
:done
if errorlevel 1 (
  echo.
  echo Installation failed. Confirm that Python 3.10+ is installed.
)
pause
