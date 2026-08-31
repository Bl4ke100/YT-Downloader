@echo off
title KRONOS 4K - Build Standalone EXE
cd /d "%~dp0"
echo ============================================================
echo   Building KRONOS 4K Standalone Executable (.exe)
echo ============================================================
python build_exe.py
echo.
pause
