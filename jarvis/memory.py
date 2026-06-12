"""Jarvis'in uzun süreli hafızası: konuşmalar JSON'a kaydedilir.

Her oturum sonunda son 20 mesaj saklanır. Sonraki başlangıçta yüklenir,
böylece Jarvis seni ve önceki konuşmaları hatırlar.
"""
import json
import os

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "memory.json")
MAX_MESSAGES = 40   # dosyada en fazla saklanan mesaj
CONTEXT_MSGS = 20   # her oturumda belleğe yüklenen mesaj sayısı


def load() -> list[dict]:
    """Önceki oturumdan son mesajları döndürür."""
    if not os.path.exists(MEMORY_FILE):
        return []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("messages", [])[-CONTEXT_MSGS:]
    except Exception:
        return []


def save(messages: list[dict]):
    """Mevcut oturumun mesajlarını diske yazar."""
    # Sadece text içerikli mesajları sakla (tool sonuçlarını değil)
    clean = []
    for m in messages:
        if isinstance(m.get("content"), str):
            clean.append({"role": m["role"], "content": m["content"]})
        elif isinstance(m.get("content"), list):
            texts = [b.get("text", "") for b in m["content"]
                     if isinstance(b, dict) and b.get("type") == "text"]
            if texts:
                clean.append({"role": m["role"], "content": " ".join(texts)})

    # Son MAX_MESSAGES mesajı tut
    existing = []
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f).get("messages", [])
        except Exception:
            pass

    merged = (existing + clean)[-MAX_MESSAGES:]
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"messages": merged}, f, ensure_ascii=False, indent=2)
