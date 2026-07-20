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
    pause
    exit /b 1
)

"%PYTHON%" -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo ONF QML dependencies are missing.
    echo Run: "%PYTHON%" -m pip install -r requirements.txt
    pause
    exit /b 1
)

if /i "%~1"=="--check" (
    echo ONF QML launcher is ready.
    exit /b 0
)

"%PYTHON%" -m onf_v2.ui_qml.preview
if errorlevel 1 (
    echo.
    echo ONF QML stopped because an error occurred.
    pause
    exit /b 1
)

exit /b 0
