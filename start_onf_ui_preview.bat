@echo off
cd /d "%~dp0"
python -m onf_v2.ui_qml.preview
if errorlevel 1 pause
