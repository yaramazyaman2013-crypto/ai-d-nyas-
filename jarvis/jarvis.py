"""JARVIS — ana döngü.

Çalıştır:
  python jarvis.py            → sürekli dinleme (Enter yok), "Jarvis" de uyan
  python jarvis.py --enter    → klasik bas-konuş modu (Enter'a bas)

İlk çalıştırmada eksik kütüphaneler otomatik yüklenir.
"""
import os
import subprocess
import sys

# ── Otomatik kurulum ────────────────────────────────────────────────────────
def _auto_install():
    req = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if not os.path.exists(req):
        return

    import importlib.util

    pkg_map = {
        "groq": "groq",
        "anthropic": "anthropic",
        "google.generativeai": "google-generativeai",
        "faster_whisper": "faster-whisper",
        "edge_tts": "edge-tts",
        "sounddevice": "sounddevice",
        "numpy": "numpy",
        "dotenv": "python-dotenv",
        "websockets": "websockets",
        "psutil": "psutil",
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
        print("✓ Python kurulumu tamamlandı.")
        print("─" * 50)

    node_modules = os.path.join(os.path.dirname(__file__), "node_modules")
    pkg_json = os.path.join(os.path.dirname(__file__), "package.json")
    if os.path.exists(pkg_json) and not os.path.exists(node_modules):
        # Node.js'i PATH'te veya yaygın Windows klasörlerinde ara
        node_exe = _find_node()
        npm_exe  = _find_npm()
        if not npm_exe:
            print("⚠ Node.js/npm bulunamadı — Minecraft botu olmadan devam.")
            print("  Çözüm: bilgisayarı yeniden başlat veya Node.js'i tekrar kur (nodejs.org)")
        else:
            try:
                print("Minecraft botu için Node.js paketleri kuruluyor...")
                subprocess.check_call(
                    [npm_exe, "install", "--silent"],
                    cwd=os.path.dirname(__file__)
                )
                print("✓ npm kurulumu tamamlandı.")
            except subprocess.CalledProcessError:
                print("⚠ npm install başarısız — Minecraft botu çalışmayabilir.")


def _find_node() -> str | None:
    """Node.js çalıştırılabilir dosyasını PATH'te veya yaygın klasörlerde bul."""
    import shutil
    if shutil.which("node"):
        return "node"
    candidates = []
    if sys.platform.startswith("win"):
        pf  = os.environ.get("ProgramFiles", "C:\\Program Files")
        pf86= os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
        appdata = os.environ.get("APPDATA", "")
        local   = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(pf,   "nodejs", "node.exe"),
            os.path.join(pf86, "nodejs", "node.exe"),
            os.path.join(appdata, "nvm", "current", "node.exe"),
            os.path.join(local,   "Programs", "nodejs", "node.exe"),
        ]
    for c in candidates:
        if os.path.isfile(c):
            # Klasörü PATH'e ekle ki npm da bulunabilsin
            os.environ["PATH"] = os.path.dirname(c) + os.pathsep + os.environ.get("PATH", "")
            return c
    return None


def _find_npm() -> str | None:
    """npm'i PATH'te veya yaygın klasörlerde bul."""
    import shutil
    _find_node()  # önce node'u bul, PATH güncellensin
    if shutil.which("npm"):
        return "npm"
    if sys.platform.startswith("win"):
        # npm.cmd Windows'ta
        if shutil.which("npm.cmd"):
            return "npm.cmd"
        pf = os.environ.get("ProgramFiles", "C:\\Program Files")
        npm_cmd = os.path.join(pf, "nodejs", "npm.cmd")
        if os.path.isfile(npm_cmd):
            return npm_cmd
    return None


def _pause_on_crash(stage: str, exc: BaseException):
    """Hata olursa pencerenin kapanmaması için hatayı göster ve bekle."""
    import traceback
    print("\n" + "═" * 50)
    print(f"HATA ({stage}) — Jarvis başlatılamadı:")
    print("═" * 50)
    traceback.print_exception(type(exc), exc, exc.__traceback__)
    print("═" * 50)
    print("\nHatayı yukarıda görebilirsin. Yardım için bu mesajı paylaş.")
    try:
        input("\nKapatmak için ENTER'a bas...")
    except Exception:
        pass
    sys.exit(1)


try:
    _auto_install()
except Exception as _e:
    _pause_on_crash("kurulum", _e)

# ── Normal import'lar ────────────────────────────────────────────────────────
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

try:
    import brain  # noqa: E402
    import voice  # noqa: E402
except Exception as _e:
    _pause_on_crash("import", _e)

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
    provider = os.getenv("JARVIS_PROVIDER", "groq").lower()

    if provider == "groq" and not os.getenv("GROQ_API_KEY"):
        print("─" * 50)
        print("Groq API anahtarı bulunamadı.")
        print("→ https://console.groq.com/keys (ücretsiz, hızlı)")
        key = input("Groq API anahtarını gir: ").strip()
        if not key:
            print("Anahtar girilmedi, çıkılıyor.")
            sys.exit(1)
        os.environ["GROQ_API_KEY"] = key
        _save_key("GROQ_API_KEY", key)
        print("─" * 50)

    elif provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
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


# ── Modlar ──────────────────────────────────────────────────────────────────
def run_push_to_talk(jarvis):
    """Klasik mod: Enter'a bas, konuş, cevabı al."""
    print("Mod: Bas-konuş  (Çıkış: Ctrl+C)")
    while True:
        audio = voice.record_until_enter()
        text = voice.transcribe(audio)
        if not text:
            print("   (ses anlaşılmadı, tekrar dene)")
            continue
        print(f"👤 Sen: {text}")
        reply = jarvis.think(text)
        print(f"🤖 Jarvis: {reply}")
        voice.speak(reply)


def run_wake_word(jarvis):
    """Sürekli dinleme modu: 'Jarvis' de, konuş."""
    print(f"Mod: Uyandırma kelimesi — '{voice.WAKE_WORD}' de  (Çıkış: Ctrl+C)")
    listener = voice.WakeWordListener(on_command=jarvis.think)
    listener.start()
    try:
        # Ana thread'i canlı tut
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(BANNER)
    _setup_keys()

    # Mikrofon kontrolü — sorun varsa korkutucu traceback yerine net mesaj göster
    try:
        voice._find_input_device()
    except voice.NoMicrophoneError as e:
        print("\n" + "═" * 50)
        print(str(e))
        print("═" * 50)
        try:
            input("\nKapatmak için ENTER'a bas...")
        except Exception:
            pass
        sys.exit(1)

    jarvis = brain.Brain()
    voice.speak("Merhaba, ben Jarvis. Emrindeyim.")

    # Varsayılan: sürekli dinleme (Enter gerekmez). --enter ile bas-konuş'a geç.
    push_mode = "--enter" in sys.argv

    try:
        if push_mode:
            run_push_to_talk(jarvis)
        else:
            run_wake_word(jarvis)
    except KeyboardInterrupt:
        print("\nGörüşürüz!")
        voice.speak("Görüşmek üzere.")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception as _e:
        _pause_on_crash("çalışma", _e)
