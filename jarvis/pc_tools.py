"""Jarvis'in bilgisayar üzerindeki elleri: program açma, ses, ekran, arama vb.

Her fonksiyon string döndürür — bu sonuç Claude'a geri verilir, o da
sana sözlü olarak özetler. Yeni yetenek eklemek için buraya fonksiyon yaz
ve TOOLS listesine şemasını ekle (brain.py otomatik kullanır).
"""
import datetime
import os
import platform
import subprocess
import sys
import webbrowser

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"


def open_app(isim: str) -> str:
    """Bir programı/uygulamayı açar."""
    isim = isim.strip()
    try:
        if IS_WIN:
            os.startfile(isim)  # type: ignore[attr-defined]
        elif IS_MAC:
            subprocess.Popen(["open", "-a", isim])
        else:
            subprocess.Popen([isim])
        return f"{isim} açıldı."
    except Exception as e:
        return f"{isim} açılamadı: {e}"


def search_web(sorgu: str) -> str:
    """Tarayıcıda web araması yapar."""
    webbrowser.open(f"https://www.google.com/search?q={sorgu}")
    return f"'{sorgu}' için arama açıldı."


def open_url(url: str) -> str:
    """Tarayıcıda bir adres açar."""
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"{url} açıldı."


def set_volume(seviye: int) -> str:
    """Sistem ses seviyesini ayarlar (0-100)."""
    seviye = max(0, min(100, int(seviye)))
    try:
        if IS_MAC:
            subprocess.run(["osascript", "-e",
                            f"set volume output volume {seviye}"], check=True)
        elif sys.platform.startswith("linux"):
            subprocess.run(["amixer", "-q", "sset", "Master", f"{seviye}%"],
                           check=True)
        elif IS_WIN:
            return ("Windows'ta ses ayarı için 'pycaw' kütüphanesi gerekir "
                    "(pip install pycaw). Şimdilik atlandı.")
        return f"Ses %{seviye} yapıldı."
    except Exception as e:
        return f"Ses ayarlanamadı: {e}"


def take_screenshot() -> str:
    """Ekran görüntüsü alıp masaüstüne kaydeder."""
    path = os.path.join(os.path.expanduser("~"), "jarvis_screenshot.png")
    try:
        if IS_MAC:
            subprocess.run(["screencapture", path], check=True)
        elif sys.platform.startswith("linux"):
            subprocess.run(["scrot", path], check=True)
        elif IS_WIN:
            return ("Windows'ta ekran görüntüsü için 'pillow' gerekir "
                    "(pip install pillow). Şimdilik atlandı.")
        return f"Ekran görüntüsü kaydedildi: {path}"
    except Exception as e:
        return f"Ekran görüntüsü alınamadı: {e}"


def get_time() -> str:
    """Tarih ve saati söyler."""
    now = datetime.datetime.now()
    return now.strftime("Bugün %d.%m.%Y, saat %H:%M.")


def system_info() -> str:
    """Bilgisayar hakkında temel bilgi verir."""
    return (f"İşletim sistemi: {platform.system()} {platform.release()}, "
            f"işlemci: {platform.processor() or 'bilinmiyor'}, "
            f"Python: {platform.python_version()}.")


# ── Claude'a tanıtılan araç şemaları ──────────────────────────────────────
# Her şema bir PC fonksiyonuna karşılık gelir. "_fn" çalıştırılacak fonksiyon.
TOOLS = [
    {
        "_fn": open_app,
        "name": "open_app",
        "description": "Bilgisayarda bir program veya uygulama açar (örn. spotify, notepad, chrome).",
        "input_schema": {
            "type": "object",
            "properties": {"isim": {"type": "string", "description": "Program adı"}},
            "required": ["isim"],
        },
    },
    {
        "_fn": search_web,
        "name": "search_web",
        "description": "Web'de arama yapar ve sonuçları tarayıcıda açar.",
        "input_schema": {
            "type": "object",
            "properties": {"sorgu": {"type": "string"}},
            "required": ["sorgu"],
        },
    },
    {
        "_fn": open_url,
        "name": "open_url",
        "description": "Tarayıcıda belirtilen web adresini açar.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    {
        "_fn": set_volume,
        "name": "set_volume",
        "description": "Sistem ses seviyesini 0-100 arasında ayarlar.",
        "input_schema": {
            "type": "object",
            "properties": {"seviye": {"type": "integer"}},
            "required": ["seviye"],
        },
    },
    {
        "_fn": take_screenshot,
        "name": "take_screenshot",
        "description": "Ekran görüntüsü alır ve kaydeder.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "_fn": get_time,
        "name": "get_time",
        "description": "Şu anki tarih ve saati verir.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "_fn": system_info,
        "name": "system_info",
        "description": "Bilgisayarın işletim sistemi ve donanım bilgisini verir.",
        "input_schema": {"type": "object", "properties": {}},
    },
]
