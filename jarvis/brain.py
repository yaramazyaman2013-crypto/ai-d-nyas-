"""Jarvis'in beyni: Claude ile düşünür ve gerektiğinde araçları (tool) çağırır.

PC araçları (pc_tools) ve Minecraft araçları (mc_bridge) tek bir araç
listesinde toplanır. Claude hangisini çağıracağına kendi karar verir.
"""
import os

import anthropic

import mc_bridge
import pc_tools

MODEL = os.getenv("JARVIS_MODEL", "claude-sonnet-4-6")

SYSTEM = (
    "Sen Jarvis'sin — kullanıcının kişisel sesli asistanı. Türkçe, kısa ve "
    "samimi konuş; gereksiz uzatma. Kullanıcı bilgisayarını kontrol etmeni "
    "(program açma, ses, arama) veya Minecraft'ta bir şey yapmanı isteyebilir. "
    "Uygun aracı çağır, sonra sonucu tek-iki cümleyle sözlü olarak özetle. "
    "Araç çağırman gerekmiyorsa sadece sohbet et. Cevapların sesli okunacağı "
    "için emoji ve madde işareti kullanma."
)

# Tüm araçları birleştir ve isimden fonksiyona harita çıkar.
_ALL_TOOLS = pc_tools.TOOLS + mc_bridge.TOOLS
_FN_MAP = {t["name"]: t["_fn"] for t in _ALL_TOOLS}
# API'ye "_fn" alanı olmadan gönder.
_API_TOOLS = [{k: v for k, v in t.items() if k != "_fn"} for t in _ALL_TOOLS]


class Brain:
    def __init__(self):
        self.client = anthropic.Anthropic()  # ANTHROPIC_API_KEY env'den
        self.history: list[dict] = []

    def think(self, user_text: str) -> str:
        """Kullanıcı metnini işler, gereken araçları çağırır, sözlü cevap döndürür."""
        self.history.append({"role": "user", "content": user_text})

        # Araç çağırma döngüsü: Claude araç isterse çalıştır, sonucu geri ver.
        while True:
            msg = self.client.messages.create(
                model=MODEL,
                max_tokens=400,
                system=SYSTEM,
                tools=_API_TOOLS,
                messages=self.history,
            )
            self.history.append({"role": "assistant", "content": msg.content})

            if msg.stop_reason != "tool_use":
                # Düz metin cevabı — topla ve döndür.
                return "".join(
                    b.text for b in msg.content if b.type == "text"
                ).strip()

            # Bir veya birden çok aracı çalıştır.
            results = []
            for block in msg.content:
                if block.type != "tool_use":
                    continue
                fn = _FN_MAP.get(block.name)
                try:
                    out = fn(**block.input) if fn else f"Bilinmeyen araç: {block.name}"
                except Exception as e:
                    out = f"Araç hatası ({block.name}): {e}"
                print(f"   🔧 {block.name}({block.input}) → {out}")
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(out),
                })
            self.history.append({"role": "user", "content": results})
