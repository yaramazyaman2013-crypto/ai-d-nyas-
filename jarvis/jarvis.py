"""JARVIS — ana döngü. Dinle → düşün → konuş.

Çalıştır:  python jarvis.py
Konuşmak için ENTER'a bas, konuş, bitince tekrar ENTER.
Çıkmak için Ctrl+C.
"""
import os
import sys

from dotenv import load_dotenv

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
    """Anahtarı .env dosyasına kalıcı olarak yazar."""
    lines = []
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # Varsa güncelle, yoksa ekle
    key_line = f"{env_var}={value}\n"
    for i, line in enumerate(lines):
        if line.startswith(f"{env_var}="):
            lines[i] = key_line
            break
    else:
        lines.append(key_line)

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"   ✓ Anahtar .env dosyasına kaydedildi (bir daha sorulmayacak).")


def _setup_keys():
    """Eksik API anahtarlarını başlangıçta kullanıcıdan iste ve kaydet."""
    provider = os.getenv("JARVIS_PROVIDER", "gemini").lower()

    if provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        print("─" * 50)
        print("Gemini API anahtarı bulunamadı.")
        print("→ https://aistudio.google.com/apikey adresinden alabilirsin.")
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
        print("→ https://console.anthropic.com adresinden alabilirsin.")
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
