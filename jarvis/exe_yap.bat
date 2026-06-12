@echo off
title JARVIS EXE Olusturucu
set "DIR=%~dp0"
pushd "%DIR%"

echo ============================================
echo  JARVIS.EXE olusturuluyor...
echo  (Ilk seferde 5-10 dakika surebilir)
echo ============================================

REM Python'u bul
set "PYTHON="
where python >nul 2>nul && set "PYTHON=python"
if not defined PYTHON (
    where py >nul 2>nul && set "PYTHON=py -3"
)
if not defined PYTHON (
    echo HATA: Python bulunamadi! python.org'dan kur ve "Add to PATH" isaretle.
    pause
    exit /b 1
)

REM Bagimliliklari ve PyInstaller'i kur
echo Paketler kuruluyor...
%PYTHON% -m pip install --quiet -r requirements.txt
%PYTHON% -m pip install --quiet pyinstaller

REM EXE olustur (bulut STT kullanildigi icin kucuk kalir)
%PYTHON% -m PyInstaller --noconfirm --onefile --console --name Jarvis --collect-all gtts --collect-all edge_tts --hidden-import sounddevice --hidden-import dotenv --exclude-module faster_whisper --exclude-module torch jarvis.py

if exist "dist\Jarvis.exe" (
    echo.
    echo ============================================
    echo  TAMAMLANDI!  dist\Jarvis.exe hazir.
    echo.
    echo  NOT: Jarvis.exe'yi bu klasorde tut veya yanina
    echo  .env dosyasini kopyala. Internet baglantisi gerekir.
    echo ============================================
) else (
    echo HATA: EXE olusturulamadi. Yukaridaki hatayi paylas.
)
pause
popd
