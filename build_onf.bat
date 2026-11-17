@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%CD%\build_onf.ps1"
if errorlevel 1 (
    echo Build or launch verification failed. Existing dist\ONF.exe was not replaced.
    pause
    exit /b 1
)

echo Verified build: "%CD%\dist\ONF.exe"
