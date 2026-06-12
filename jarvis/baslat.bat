@echo off
chcp 65001 >nul
title JARVIS
cd /d "%~dp0"

REM ── Python bul ────────────────────────────────────────────────────────────
where py >nul 2>nul
if %errorlevel%==0 (set PYTHON=py) else (set PYTHON=python)

REM ── Node.js'i PATH'te veya yaygın kurulum klasörlerinde ara ──────────────
set NODE=
where node >nul 2>nul
if %errorlevel%==0 (
    set NODE=node
    goto node_found
)

REM Yaygın Node.js kurulum yolları
for %%P in (
    "%ProgramFiles%\nodejs\node.exe"
    "%ProgramFiles(x86)%\nodejs\node.exe"
    "%APPDATA%\nvm\current\node.exe"
    "%LOCALAPPDATA%\Programs\nodejs\node.exe"
    "%ProgramFiles%\nvm\current\node.exe"
) do (
    if exist %%P (
        set NODE=%%P
        REM Klasörü PATH'e geçici ekle
        for %%D in (%%P) do set "PATH=%PATH%;%%~dpD"
        goto node_found
    )
)

echo.
echo *** NODE.JS BULUNAMADI ***
echo Node.js kurulu olmasına rağmen bulunamıyorsa:
echo   1. Bilgisayarı yeniden başlat (kurulum PATH'i henüz uygulanmamış olabilir)
echo   2. Veya Node.js'i buradan tekrar kur: https://nodejs.org (LTS)
echo      Kurulumda "Add to PATH" seçeneği işaretli olmalı.
echo   3. Minecraft botu çalışmayacak ama sesli asistan çalışır.
echo.
set NODE=
goto start_jarvis

:node_found
echo [OK] Node.js bulundu: %NODE%

REM ── node_modules yoksa npm install çalıştır ───────────────────────────────
if not exist "%~dp0node_modules" (
    echo Minecraft botu için paketler kuruluyor...
    npm install --prefix "%~dp0" --silent
    if %errorlevel% neq 0 (
        echo [UYARI] npm install basarisiz. Minecraft botu calismayabilir.
    ) else (
        echo [OK] npm kurulumu tamamlandi.
    )
)

:start_jarvis
echo.
echo JARVIS baslatiliyor...
%PYTHON% jarvis.py %*

echo.
echo Jarvis kapandi.
pause
