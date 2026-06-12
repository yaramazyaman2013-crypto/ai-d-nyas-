"""JARVIS — ana döngü. Dinle → düşün → konuş.

Çalıştır:  python jarvis.py
İlk çalıştırmada gerekli kütüphaneler otomatik yüklenir.
Konuşmak için ENTER'a bas, konuş, bitince tekrar ENTER.
Çıkmak için Ctrl+C.
"""
import os
import subprocess
import sys

# ── Otomatik kurulum (diğer import'lardan önce) ────────────────────────────
def _auto_install():
    req = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if not os.path.exists(req):
        return

    # Hangi paketler eksik?
    import importlib.util

    pkg_map = {
        "anthropic": "anthropic",
        "google.generativeai": "google-generativeai",
        "faster_whisper": "faster-whisper",
        "edge_tts": "edge-tts",
        "sounddevice": "sounddevice",
        "numpy": "numpy",
        "dotenv": "python-dotenv",
        "websockets": "websockets",
    }

    missing = [
        pip for mod, pip in pkg_map.items()
        if importlib.util.find_spec(mod.split(".")[0]) is None
    ]

    if missing:
        print("─" * 50)
        print(f"Eksik kütüphaneler kuruluyor: {', '.join(missing)}")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "-r", req]
        )
        print("✓ Kurulum tamamlandı.")
        print("─" * 50)

    # Node.js bağımlılıkları (bot.js için)
    node_modules = os.path.join(os.path.dirname(__file__), "node_modules")
    pkg_json = os.path.join(os.path.dirname(__file__), "package.json")
    if os.path.exists(pkg_json) and not os.path.exists(node_modules):
        try:
            print("Minecraft botu için Node.js paketleri kuruluyor...")
            subprocess.check_call(
                ["npm", "install", "--silent"],
                cwd=os.path.dirname(__file__)
            )
            print("✓ npm kurulum tamamlandı.")
        except FileNotFoundError:
            print("⚠ Node.js bulunamadı — Minecraft botu için nodejs kur.")
        except subprocess.CalledProcessError:
            print("⚠ npm install başarısız — Minecraft botu çalışmayabilir.")


_auto_install()

# ── Normal import'lar (kurulum sonrası) ───────────────────────────────────
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import brain  # noqa: E402
import voice  # noqa: E402

BANNER = r"""
   ___  ____  ____  _   _ ___ ____
  |_  |/ _  \|  _ \| | | |_ _/ ___|
   | || (_| || |_) | | | || |\___ \
  _/ /  \__,_|  _ <| |_| || | ___) |
 |___/       |_| \_\\___/|___|____/
   Sesli Asistan + Minecraft Botu
"""

ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")


def _save_key(env_var: str, value: str):
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
    key_line = f"{env_var}={value}\n"
    for i, line in enumerate(lines):
        if line.startswith(f"{env_var}="):
            lines[i] = key_line
            break
    else:
        lines.append(key_line)
    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print("   ✓ Anahtar kaydedildi, bir daha sorulmayacak.")


def _setup_keys():
    provider = os.getenv("JARVIS_PROVIDER", "gemini").lower()

    if provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        print("─" * 50)
        print("Gemini API anahtarı bulunamadı.")
        print("→ https://aistudio.google.com/apikey")
        key = input("Gemini API anahtarını gir: ").strip()
        if not key:
            print("Anahtar girilmedi, çıkılıyor.")
            sys.exit(1)
        os.environ["GEMINI_API_KEY"] = key
        _save_key("GEMINI_API_KEY", key)
        print("─" * 50)

    elif provider == "claude" and not os.getenv("ANTHROPIC_API_KEY"):
        print("─" * 50)
        print("Claude API anahtarı bulunamadı.")
        print("→ https://console.anthropic.com")
        key = input("Anthropic API anahtarını gir: ").strip()
        if not key:
            print("Anahtar girilmedi, çıkılıyor.")
            sys.exit(1)
        os.environ["ANTHROPIC_API_KEY"] = key
        _save_key("ANTHROPIC_API_KEY", key)
        print("─" * 50)


def main():
    print(BANNER)
    _setup_keys()

    jarvis = brain.Brain()
    voice.speak("Merhaba, ben Jarvis. Emrindeyim.")
    print("Hazırım. (Çıkış: Ctrl+C)")

    while True:
        try:
            audio = voice.record_until_enter()
            text = voice.transcribe(audio)
            if not text:
                print("   (ses anlaşılmadı, tekrar dene)")
                continue

            print(f"👤 Sen: {text}")
            reply = jarvis.think(text)
            print(f"🤖 Jarvis: {reply}")
            voice.speak(reply)

        except KeyboardInterrupt:
            print("\nGörüşürüz!")
            voice.speak("Görüşmek üzere.")
            sys.exit(0)
        except Exception as e:
            print(f"[hata] {e}")


if __name__ == "__main__":
    main()
