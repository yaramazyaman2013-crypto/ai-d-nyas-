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


def media_control(action: str) -> str:
    """Medyayı kontrol eder: play_pause, next, previous, stop."""
    try:
        if IS_MAC:
            applescript = {
                "play_pause": 'tell application "Spotify" to playpause',
                "next": 'tell application "Spotify" to next track',
                "previous": 'tell application "Spotify" to previous track',
            }
            script = applescript.get(action, "")
            if script:
                subprocess.run(["osascript", "-e", script], check=True)
        elif sys.platform.startswith("linux"):
            cmd_map = {
                "play_pause": ["playerctl", "play-pause"],
                "next": ["playerctl", "next"],
                "previous": ["playerctl", "previous"],
                "stop": ["playerctl", "stop"],
            }
            subprocess.run(cmd_map.get(action, ["true"]), check=True)
        elif IS_WIN:
            import ctypes
            vk = {"play_pause": 0xB3, "next": 0xB0, "previous": 0xB1, "stop": 0xB2}
            code = vk.get(action)
            if code:
                ctypes.windll.user32.keybd_event(code, 0, 0, 0)
                ctypes.windll.user32.keybd_event(code, 0, 2, 0)
        return f"Medya: {action} yapıldı."
    except Exception as e:
        return f"Medya kontrolü başarısız: {e}"


def lock_screen() -> str:
    """Ekranı/bilgisayarı kilitler."""
    try:
        if IS_MAC:
            subprocess.run(["pmset", "displaysleepnow"], check=True)
        elif sys.platform.startswith("linux"):
            for cmd in (["gnome-screensaver-command", "-l"],
                        ["xdg-screensaver", "lock"],
                        ["loginctl", "lock-session"]):
                try:
                    subprocess.run(cmd, check=True)
                    break
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
        elif IS_WIN:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        return "Ekran kilitlendi."
    except Exception as e:
        return f"Kilitleme başarısız: {e}"


def clipboard_copy(metin: str) -> str:
    """Metni panoya kopyalar."""
    try:
        if IS_MAC:
            subprocess.run(["pbcopy"], input=metin.encode(), check=True)
        elif sys.platform.startswith("linux"):
            subprocess.run(["xclip", "-selection", "clipboard"],
                           input=metin.encode(), check=True)
        elif IS_WIN:
            subprocess.run(["clip"], input=metin.encode("utf-16"), check=True)
        return f"Panoya kopyalandı: {metin[:50]}{'...' if len(metin)>50 else ''}"
    except Exception as e:
        return f"Kopyalama başarısız: {e}"


def type_text(metin: str) -> str:
    """Klavyeyle metin yazar (aktif pencereye)."""
    try:
        if IS_MAC:
            subprocess.run(["osascript", "-e",
                            f'tell application "System Events" to keystroke "{metin}"'])
        elif sys.platform.startswith("linux"):
            subprocess.run(["xdotool", "type", "--clearmodifiers", metin])
        elif IS_WIN:
            import ctypes
            for ch in metin:
                vk = ctypes.windll.user32.VkKeyScanW(ch)
                ctypes.windll.user32.keybd_event(vk & 0xff, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk & 0xff, 0, 2, 0)
        return f"Yazıldı: {metin[:50]}"
    except Exception as e:
        return f"Yazma başarısız: {e}"


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
    {
        "_fn": media_control,
        "name": "media_control",
        "description": "Müzik/medya çalar kontrolü: play_pause (oynat/durdur), next (sonraki), previous (önceki), stop.",
        "input_schema": {
            "type": "object",
            "properties": {"action": {"type": "string", "enum": ["play_pause", "next", "previous", "stop"]}},
            "required": ["action"],
        },
    },
    {
        "_fn": lock_screen,
        "name": "lock_screen",
        "description": "Bilgisayar ekranını kilitler.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "_fn": clipboard_copy,
        "name": "clipboard_copy",
        "description": "Bir metni panoya kopyalar.",
        "input_schema": {
            "type": "object",
            "properties": {"metin": {"type": "string"}},
            "required": ["metin"],
        },
    },
    {
        "_fn": type_text,
        "name": "type_text",
        "description": "Aktif pencereye klavyeyle metin yazar.",
        "input_schema": {
            "type": "object",
            "properties": {"metin": {"type": "string"}},
            "required": ["metin"],
        },
    },
]
