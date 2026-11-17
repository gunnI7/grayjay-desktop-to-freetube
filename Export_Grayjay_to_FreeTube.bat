@echo off
setlocal
title Grayjay Desktop to FreeTube Playlist Exporter
cd /d "%~dp0"

echo ========================================================
echo   Grayjay Desktop -^> FreeTube Playlist Exporter
echo ========================================================
echo.

set "SCRIPT=%~dp0grayjay_to_freetube.py"

if not exist "%SCRIPT%" (
    echo [ERROR] grayjay_to_freetube.py was not found next to this file.
    echo Make sure you extracted the entire ZIP archive into the same folder.
    echo.
    pause
    exit /b 1
)

set "PYTHON_CMD="

py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto :run_script
)

python -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :run_script
)

python3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python3"
    goto :run_script
)

echo [ERROR] Python 3 was not found on this computer.
echo.
echo Install Python 3 from:
echo   https://www.python.org/downloads/
echo.
echo IMPORTANT: Check "Add python.exe to PATH" during installation,
echo then double-click this file again.
echo.
pause
exit /b 1

:run_script
if "%~1"=="" (
    %PYTHON_CMD% "%SCRIPT%"
) else (
    %PYTHON_CMD% "%SCRIPT%" "%~1"
)

echo.
pause
endlocal
