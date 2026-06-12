"""Jarvis'in kulağı ve ağzı: mikrofon (Whisper STT) + sesli cevap (edge-tts)."""
import asyncio
import os
import queue
import sys
import tempfile

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000

_whisper_model = None


def _get_whisper():
    """Whisper modelini tembel yükle (ilk kullanımda indirilir)."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        size = os.getenv("JARVIS_STT_MODEL", "small")
        print(f"[voice] Whisper '{size}' yükleniyor...")
        _whisper_model = WhisperModel(size, device="cpu", compute_type="int8")
    return _whisper_model


def record_until_enter() -> np.ndarray:
    """Bas-konuş: Enter'a basınca kayda başlar, tekrar Enter'a basınca biter."""
    input("\n🎤 Konuşmak için ENTER'a bas...")
    print("   ● Kayıt... (bitince ENTER)")

    frames = queue.Queue()

    def callback(indata, *_):
        frames.put(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32",
                        callback=callback):
        input()  # ikinci Enter kaydı durdurur

    chunks = []
    while not frames.empty():
        chunks.append(frames.get())
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks, axis=0).flatten()


def transcribe(audio: np.ndarray) -> str:
    """Ses dalgasını Türkçe metne çevirir."""
    if audio.size < SAMPLE_RATE // 2:  # 0.5sn'den kısa
        return ""
    model = _get_whisper()
    segments, _ = model.transcribe(audio, language="tr", beam_size=1)
    return " ".join(s.text for s in segments).strip()


async def _speak_async(text: str):
    import edge_tts

    voice = os.getenv("JARVIS_VOICE", "tr-TR-AhmetNeural")
    path = os.path.join(tempfile.gettempdir(), "jarvis_out.mp3")
    await edge_tts.Communicate(text, voice).save(path)
    _play(path)


def speak(text: str):
    """Metni sesli okur."""
    if not text:
        return
    asyncio.run(_speak_async(text))


def _play(path: str):
    """mp3'ü platformdan bağımsız çal (harici oynatıcı çağırır)."""
    import subprocess

    try:
        if sys.platform == "darwin":
            subprocess.run(["afplay", path], check=False)
        elif sys.platform.startswith("win"):
            # PowerShell ile çal — ek bağımlılık gerektirmez
            subprocess.run(
                ["powershell", "-c",
                 f"(New-Object Media.SoundPlayer);"
                 f"Add-Type -AssemblyName presentationCore;"
                 f"$p=New-Object System.Windows.Media.MediaPlayer;"
                 f"$p.Open('{path}');$p.Play();Start-Sleep 10"],
                check=False)
        else:
            # Linux: ffplay/mpg123 dene
            for player in (["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
                           ["mpg123", "-q", path]):
                try:
                    subprocess.run(player, check=True)
                    break
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
    except Exception as e:
        print(f"[voice] ses çalınamadı: {e}")
