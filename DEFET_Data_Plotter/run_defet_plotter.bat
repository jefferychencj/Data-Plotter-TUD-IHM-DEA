@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 defet_data_plotter.py
  goto :check
)
python defet_data_plotter.py
:check
if not errorlevel 1 exit /b 0
echo.
echo The application could not start.
echo Install Python 3.10+ and run install_requirements.bat.
pause
