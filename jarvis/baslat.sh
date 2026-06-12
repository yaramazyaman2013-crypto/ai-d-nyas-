#!/usr/bin/env bash
# JARVIS başlatıcı (Mac/Linux)
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
else
    PYTHON=python
fi

echo "JARVIS başlatılıyor..."
"$PYTHON" jarvis.py "$@"

echo
read -r -p "Jarvis kapandı. Kapatmak için ENTER'a bas..."
