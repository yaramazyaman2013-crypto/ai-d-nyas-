@echo off
title JARVIS
chcp 65001 >nul

set "DIR=%~dp0"
pushd "%DIR%"

REM --- Python ---
set PYTHON=
where py >nul 2>nul && set PYTHON=py
if "%PYTHON%"=="" where python >nul 2>nul && set PYTHON=python
if "%PYTHON%"=="" (
    echo Python bulunamadi. python.org adresinden kur.
    pause & exit /b 1
)

REM --- Node.js PATH ---
where node >nul 2>nul
if errorlevel 1 (
    if exist "%ProgramFiles%\nodejs" set "PATH=%ProgramFiles%\nodejs;%PATH%"
    if exist "%LOCALAPPDATA%\Programs\nodejs" set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%"
    if exist "%APPDATA%\nvm\current" set "PATH=%APPDATA%\nvm\current;%PATH%"
)

REM --- npm install (sadece node_modules yoksa) ---
if not exist "node_modules" (
    where npm >nul 2>nul
    if not errorlevel 1 (
        echo npm install calisiyor...
        npm install
    )
)

REM --- Jarvis ---
echo.
%PYTHON% jarvis.py %*

echo.
echo Jarvis kapandi.
pause
popd
