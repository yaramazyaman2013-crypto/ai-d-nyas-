@echo off
chcp 65001 >nul
title JARVIS
cd /d "%~dp0"

REM ── Python bul ────────────────────────────────────────────────────────────
set PYTHON=
where py >nul 2>nul
if %errorlevel%==0 set PYTHON=py
if "%PYTHON%"=="" (
    where python >nul 2>nul
    if %errorlevel%==0 set PYTHON=python
)
if "%PYTHON%"=="" (
    where python3 >nul 2>nul
    if %errorlevel%==0 set PYTHON=python3
)
if "%PYTHON%"=="" (
    echo.
    echo *** PYTHON BULUNAMADI ***
    echo Python'u kur: https://www.python.org/downloads
    echo Kurulumda "Add Python to PATH" kutusunu isaretle!
    echo.
    pause
    exit /b 1
)
echo [OK] Python bulundu: %PYTHON%

REM ── Node.js PATH'e ekle (kuruluysa ama PATH'te yoksa) ─────────────────────
where node >nul 2>nul
if %errorlevel% neq 0 (
    if exist "%ProgramFiles%\nodejs\node.exe" (
        set "PATH=%ProgramFiles%\nodejs;%PATH%"
    )
    if exist "%ProgramFiles(x86)%\nodejs\node.exe" (
        set "PATH=%ProgramFiles(x86)%\nodejs;%PATH%"
    )
    if exist "%LOCALAPPDATA%\Programs\nodejs\node.exe" (
        set "PATH=%LOCALAPPDATA%\Programs\nodejs;%PATH%"
    )
    if exist "%APPDATA%\nvm\current\node.exe" (
        set "PATH=%APPDATA%\nvm\current;%PATH%"
    )
)

where node >nul 2>nul
if %errorlevel%==0 (
    echo [OK] Node.js bulundu.
) else (
    echo [UYARI] Node.js bulunamadi. Minecraft botu calismayadabilir.
    echo   Cozum: nodejs.org'dan LTS indir ve bilgisayari yeniden baslatit.
)

REM ── node_modules yoksa npm install calistir ───────────────────────────────
if not exist "%~dp0node_modules" (
    where npm >nul 2>nul
    if %errorlevel%==0 (
        echo Minecraft botu icin paketler kuruluyor...
        npm install --prefix "%~dp0" --silent
    )
)

REM ── Jarvis'i baslat ──────────────────────────────────────────────────────
echo.
echo JARVIS baslatiliyor...
echo.
%PYTHON% "%~dp0jarvis.py" %*

echo.
echo Jarvis kapandi.
pause
