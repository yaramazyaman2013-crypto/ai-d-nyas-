@echo off
chcp 65001 >nul
title JARVIS
cd /d "%~dp0"

REM Python'u bul (py launcher veya python)
where py >nul 2>nul
if %errorlevel%==0 (
    set PYTHON=py
) else (
    set PYTHON=python
)

echo JARVIS baslatiliyor...
%PYTHON% jarvis.py %*

echo.
echo Jarvis kapandi.
pause
