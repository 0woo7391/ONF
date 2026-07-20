@echo off
setlocal
cd /d "%~dp0"

set "PYTHON="

if exist ".venv\Scripts\python.exe" (
    set "PYTHON=%CD%\.venv\Scripts\python.exe"
)

if not defined PYTHON if exist "venv\Scripts\python.exe" (
    set "PYTHON=%CD%\venv\Scripts\python.exe"
)

if not defined PYTHON (
    for /f "delims=" %%P in ('where python.exe 2^>nul') do if not defined PYTHON (
        set "PYTHON=%%P"
    )
)

if not defined PYTHON (
    for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%~fD\python.exe" (
        set "PYTHON=%%~fD\python.exe"
    )
)

if not defined PYTHON (
    echo Python was not found.
    echo Install Python 3.11 or create a .venv in this folder.
    pause
    exit /b 1
)

"%PYTHON%" -c "import cv2, mediapipe, PySide6" >nul 2>&1
if errorlevel 1 (
    echo ONF dependencies are missing.
    echo Run: "%PYTHON%" -m pip install -r requirements.txt
    pause
    exit /b 1
)

if /i "%~1"=="--check" (
    echo ONF launcher is ready.
    exit /b 0
)

echo Starting ONF...
"%PYTHON%" "%CD%\main.py"
if errorlevel 1 (
    echo.
    echo ONF stopped because an error occurred.
    echo Copy the message above when reporting the problem.
    pause
    exit /b 1
)

exit /b 0
