"""Jarvis'in kulağı ve ağzı.

İki dinleme modu:
  - record_until_enter()  → klasik bas-konuş (Enter)
  - listen_for_wake_word() → sürekli dinler, "Jarvis" duyunca uyanır

Ses çıkışı: edge-tts ile Türkçe konuşma.
"""
import asyncio
import os
import queue
import sys
import tempfile
import threading

# Hugging Face indirme uyarılarını sustur (zararsız ama kafa karıştırıcı)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000
WAKE_WORD = os.getenv("JARVIS_WAKE_WORD", "jarvis").lower()

_whisper_model = None
_MIC_DEVICE = None  # seçili giriş cihazı (index)


class NoMicrophoneError(RuntimeError):
    """Mikrofon bulunamadığında fırlatılır — anlaşılır talimat içerir."""


def list_audio_devices() -> str:
    """Tüm ses cihazlarını okunabilir biçimde döndürür (tanılama için)."""
    try:
        lines = []
        for i, d in enumerate(sd.query_devices()):
            io = []
            if d["max_input_channels"] > 0:
                io.append(f"giriş:{d['max_input_channels']}")
            if d["max_output_channels"] > 0:
                io.append(f"çıkış:{d['max_output_channels']}")
            lines.append(f"  [{i}] {d['name']}  ({', '.join(io)})")
        return "\n".join(lines) if lines else "  (hiç cihaz yok)"
    except Exception as e:
        return f"  (cihazlar listelenemedi: {e})"


def _find_input_device() -> int:
    """Geçerli bir mikrofon bul. Yoksa anlaşılır NoMicrophoneError fırlatır."""
    global _MIC_DEVICE
    if _MIC_DEVICE is not None:
        return _MIC_DEVICE

    # 1) Kullanıcı .env'de elle belirtmişse (numara veya isim)
    env = os.getenv("JARVIS_MIC", "").strip()
    if env:
        try:
            _MIC_DEVICE = int(env)
            return _MIC_DEVICE
        except ValueError:
            for i, d in enumerate(sd.query_devices()):
                if env.lower() in d["name"].lower() and d["max_input_channels"] > 0:
                    _MIC_DEVICE = i
                    return _MIC_DEVICE

    # 2) Varsayılan giriş cihazı geçerli mi?
    try:
        default_in = sd.default.device[0]
        if default_in is not None and default_in >= 0:
            if sd.query_devices(default_in)["max_input_channels"] > 0:
                _MIC_DEVICE = default_in
                return _MIC_DEVICE
    except Exception:
        pass

    # 3) İlk kullanılabilir giriş cihazını seç
    try:
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                _MIC_DEVICE = i
                print(f"[voice] Mikrofon otomatik seçildi: [{i}] {d['name']}")
                return _MIC_DEVICE
    except Exception:
        pass

    raise NoMicrophoneError(
        "MİKROFON BULUNAMADI! Lütfen şunları kontrol et:\n"
        "  1. Bir mikrofon takılı/bağlı mı? (kulaklık mikrofonu da olur)\n"
        "  2. Windows: Ayarlar > Gizlilik ve güvenlik > Mikrofon →\n"
        "     'Uygulamaların mikrofonunuza erişmesine izin verin' AÇIK olmalı.\n"
        "  3. Windows: Ayarlar > Sistem > Ses > Giriş → bir mikrofon seçili olmalı.\n"
        "\n"
        "Mevcut ses cihazların:\n"
        f"{list_audio_devices()}\n"
        "\n"
        "Belirli bir mikrofon seçmek için jarvis/.env dosyasına şunu ekle:\n"
        "  JARVIS_MIC=1     (yukarıdaki listede 'giriş' yazan bir numara)"
    )


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # "tiny" varsayılan — CPU'da ~3x daha hızlı, Türkçe için yeterli
        # Daha iyi doğruluk istersen .env'e JARVIS_STT_MODEL=small yaz
        size = os.getenv("JARVIS_STT_MODEL", "tiny")
        print(f"[voice] Whisper '{size}' yükleniyor "
              f"(ilk seferde model indirilir, biraz bekle)...")
        _whisper_model = WhisperModel(size, device="cpu", compute_type="int8")
        print("[voice] Whisper hazır.")
    return _whisper_model


# ── Bas-konuş modu ──────────────────────────────────────────────────────────
def record_until_enter() -> np.ndarray:
    """Enter'a basınca kayıt başlar, tekrar Enter'a basınca biter."""
    input("\n🎤 Konuşmak için ENTER'a bas...")
    print("   ● Kayıt... (bitince ENTER)")

    frames: queue.Queue = queue.Queue()

    def callback(indata, *_):
        frames.put(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                        dtype="float32", callback=callback,
                        device=_find_input_device()):
        input()

    chunks = []
    while not frames.empty():
        chunks.append(frames.get())
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks, axis=0).flatten()


# ── Sürekli dinleme + uyandırma kelimesi ────────────────────────────────────
class WakeWordListener:
    """Arka planda sürekli mikrofonu dinler.

    Ses seviyesi eşiği geçince kayıt başlar, sustukça biter.
    Transkript "jarvis" içeriyorsa callback çağrılır; içermiyorsa sessizce atar.

    Kullanım:
        listener = WakeWordListener(on_command=jarvis.think)
        listener.start()   # arka planda çalışır
        listener.stop()    # durdur
    """

    CHUNK = 512           # her seferinde okunan sample sayısı
    SILENCE_THRESHOLD = 0.015   # RMS eşiği — altıysa sessiz
    SILENCE_SECS = 1.0    # bu kadar sessizlik = konuşma bitti (hız için 1.5→1.0)
    MAX_RECORD_SECS = 12  # tek konuşma en fazla bu kadar

    def __init__(self, on_command):
        self._on_command = on_command  # fn(metin: str) -> str
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print(f"[voice] Sürekli dinleme aktif — uyandırma kelimesi: '{WAKE_WORD}'")

    def stop(self):
        self._running = False

    # ── iç döngü ──────────────────────────────────────────────────────────
    def _loop(self):
        buf: queue.Queue = queue.Queue()

        def cb(indata, *_):
            buf.put(indata.copy())

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                            dtype="float32", blocksize=self.CHUNK, callback=cb,
                            device=_find_input_device()):
            while self._running:
                chunk = buf.get()
                rms = float(np.sqrt(np.mean(chunk ** 2)))
                if rms < self.SILENCE_THRESHOLD:
                    continue

                # Ses başladı — kayda geç
                print("   ◉ Dinleniyor...")
                frames = [chunk]
                silence_count = 0
                max_chunks = int(self.MAX_RECORD_SECS * SAMPLE_RATE / self.CHUNK)

                for _ in range(max_chunks):
                    c = buf.get()
                    frames.append(c)
                    if float(np.sqrt(np.mean(c ** 2))) < self.SILENCE_THRESHOLD:
                        silence_count += 1
                    else:
                        silence_count = 0
                    if silence_count >= int(self.SILENCE_SECS * SAMPLE_RATE / self.CHUNK):
                        break

                audio = np.concatenate(frames, axis=0).flatten()
                print("   ⏳ Düşünüyor...")
                text = transcribe(audio)
                if not text:
                    continue

                if WAKE_WORD in text.lower():
                    # Uyandırma kelimesini temizle
                    clean = text.lower().replace(WAKE_WORD, "").strip(" ,.")
                    if not clean:
                        speak("Evet?")
                        clean = _listen_once(buf)  # cevabı bekle
                    if clean:
                        print(f"👤 Sen: {clean}")
                        reply = self._on_command(clean)
                        print(f"🤖 Jarvis: {reply}")
                        speak(reply)


def _listen_once(buf: queue.Queue) -> str:
    """Ses başlayana kadar bekle, bitince transkript döndür."""
    import time
    deadline = time.time() + 5  # 5 saniye içinde konuşmazsa boş dön
    while time.time() < deadline:
        chunk = buf.get(timeout=1)
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        if rms < WakeWordListener.SILENCE_THRESHOLD:
            continue
        frames = [chunk]
        silence = 0
        for _ in range(int(10 * SAMPLE_RATE / WakeWordListener.CHUNK)):
            c = buf.get()
            frames.append(c)
            if float(np.sqrt(np.mean(c ** 2))) < WakeWordListener.SILENCE_THRESHOLD:
                silence += 1
            else:
                silence = 0
            if silence >= int(1.5 * SAMPLE_RATE / WakeWordListener.CHUNK):
                break
        audio = np.concatenate(frames, axis=0).flatten()
        return transcribe(audio)
    return ""


# ── Transkripsiyon ──────────────────────────────────────────────────────────
def transcribe(audio: np.ndarray) -> str:
    if audio.size < SAMPLE_RATE // 2:
        return ""
    model = _get_whisper()
    segments, _ = model.transcribe(audio, language="tr", beam_size=1)
    return " ".join(s.text for s in segments).strip()


# ── Sesli cevap ─────────────────────────────────────────────────────────────
async def _speak_async(text: str):
    import edge_tts
    voice = os.getenv("JARVIS_VOICE", "tr-TR-AhmetNeural")
    path = os.path.join(tempfile.gettempdir(), "jarvis_out.mp3")
    await edge_tts.Communicate(text, voice).save(path)
    _play(path)


def speak(text: str):
    if not text:
        return
    asyncio.run(_speak_async(text))


def _play(path: str):
    import subprocess
    try:
        if sys.platform == "darwin":
            subprocess.run(["afplay", path], check=False)
        elif sys.platform.startswith("win"):
            subprocess.run(
                ["powershell", "-c",
                 f"Add-Type -AssemblyName presentationCore;"
                 f"$p=New-Object System.Windows.Media.MediaPlayer;"
                 f"$p.Open('{path}');$p.Play();Start-Sleep 10"],
                check=False)
        else:
            for player in (
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
                ["mpg123", "-q", path],
            ):
                try:
                    subprocess.run(player, check=True)
                    break
                except (FileNotFoundError, subprocess.CalledProcessError):
                    continue
    except Exception as e:
        print(f"[voice] ses çalınamadı: {e}")
