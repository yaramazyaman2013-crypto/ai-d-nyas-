"""JARVIS — ana döngü. Dinle → düşün → konuş.

Çalıştır:  python jarvis.py
Konuşmak için ENTER'a bas, konuş, bitince tekrar ENTER.
Çıkmak için boş konuşma yap ya da Ctrl+C.
"""
import sys

from dotenv import load_dotenv

load_dotenv()

import brain  # noqa: E402  (load_dotenv'den sonra import şart)
import voice  # noqa: E402

BANNER = r"""
   ___  ____  ____  _   _ ___ ____
  |_  |/ _  \|  _ \| | | |_ _/ ___|
   | || (_| || |_) | | | || |\___ \
  _/ /  \__,_|  _ <| |_| || | ___) |
 |___/       |_| \_\\___/|___|____/
   Sesli Asistan + Minecraft Botu
"""


def main():
    print(BANNER)
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
