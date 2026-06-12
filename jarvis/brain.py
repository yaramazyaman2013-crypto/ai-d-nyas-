"""Jarvis'in beyni: Claude veya Gemini ile düşünür, araçları (tool) çağırır.

Hangi beyin kullanılacağı JARVIS_PROVIDER ortam değişkeniyle seçilir:
  JARVIS_PROVIDER=claude  → Anthropic Claude (ANTHROPIC_API_KEY gerekir)
  JARVIS_PROVIDER=gemini  → Google Gemini   (GEMINI_API_KEY gerekir)  ← varsayılan
"""
import os

import mc_bridge
import memory
import pc_tools

PROVIDER = os.getenv("JARVIS_PROVIDER", "gemini").lower()

SYSTEM = (
    "Sen Jarvis'sin — kullanıcının kişisel sesli asistanı ve Minecraft arkadaşı. "
    "Türkçe, kısa ve samimi konuş; gereksiz uzatma. "
    "Kullanıcı bilgisayarını kontrol etmeni veya Minecraft'ta görev yapmanı isteyebilir. "

    "Minecraft yeteneklerin: gel, takip et, dur, ağaç kes, blok topla, saldır, "
    "durum bildir, craft yap, yemek ye, uyu, envanter göster, eşya bırak/kuşan, "
    "koordinata git, "
    "MADEN GÖREVI (mc_mine_mission): 'kömür kaz', 'demir getir', 'elmas bul' gibi isteklerde — "
    "ore türünü ve miktarı belirle, botu gönder, döndüğünde sonucu söyle; "
    "İNŞAAT (mc_build): 'kulübe yap', 'kule inşa et', 'gökdelen yap' gibi isteklerde — "
    "yapı türünü seç (kulübe/kule/gökdelen/köprü/duvar), malzemeyi envantere göre seç; "
    "HAYATtA KALMA (mc_survive): 'hayatta kal', 'kendini yönet' isteklerinde. "

    "Maden isimleri Türkçe-İngilizce eşleştirmesi: "
    "kömür=coal, demir=iron, altın=gold, elmas=diamond, "
    "lapis=lapis, kırmızıtaş=redstone, zümrüt=emerald, bakır=copper. "

    "Kullanıcı 'bize' veya 'bize birlikte' diyorsa inşaat/maden görevini başlat. "
    "Araç çağırman gerekmiyorsa sadece sohbet et. "
    "Önceki konuşmaları hatırlıyorsun. "
    "Cevapların sesli okunacağı için emoji ve madde işareti kullanma."
)

_ALL_TOOLS = pc_tools.TOOLS + mc_bridge.TOOLS
_FN_MAP = {t["name"]: t["_fn"] for t in _ALL_TOOLS}
_API_TOOLS_CLAUDE = [{k: v for k, v in t.items() if k != "_fn"} for t in _ALL_TOOLS]


# ── Araç çalıştırma (ortak) ────────────────────────────────────────────────
def _run_tool(name: str, kwargs: dict) -> str:
    fn = _FN_MAP.get(name)
    try:
        out = fn(**kwargs) if fn else f"Bilinmeyen araç: {name}"
    except Exception as e:
        out = f"Araç hatası ({name}): {e}"
    print(f"   🔧 {name}({kwargs}) → {out}")
    return str(out)


# ── Gemini ─────────────────────────────────────────────────────────────────
def _gemini_tools_schema():
    decls = []
    for t in _ALL_TOOLS:
        schema = {k: v for k, v in t["input_schema"].items() if k != "$schema"}
        decls.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": schema,
        })
    return [{"function_declarations": decls}]


class _GeminiBrain:
    def __init__(self):
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY ortam değişkeni eksik.")
        genai.configure(api_key=api_key)
        model_name = os.getenv("JARVIS_MODEL", "gemini-2.0-flash")
        self._genai = genai
        self._model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM,
            tools=_gemini_tools_schema(),
        )
        # Hafızadan geçmiş yükle
        past = memory.load()
        history = []
        for m in past:
            role = "user" if m["role"] == "user" else "model"
            history.append({"role": role, "parts": [m["content"]]})
        self._chat = self._model.start_chat(history=history)
        self.history = past  # kayıt için

    def think(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})
        response = self._chat.send_message(user_text)

        while True:
            fn_calls = [
                p.function_call for p in response.parts
                if hasattr(p, "function_call") and p.function_call.name
            ]
            if not fn_calls:
                reply = response.text.strip()
                self.history.append({"role": "assistant", "content": reply})
                memory.save(self.history)
                return reply

            results = []
            for call in fn_calls:
                out = _run_tool(call.name, dict(call.args))
                results.append(
                    self._genai.protos.Part(
                        function_response=self._genai.protos.FunctionResponse(
                            name=call.name,
                            response={"result": out},
                        )
                    )
                )
            response = self._chat.send_message(results)


# ── Claude ─────────────────────────────────────────────────────────────────
class _ClaudeBrain:
    def __init__(self):
        import anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY ortam değişkeni eksik.")
        self.client = anthropic.Anthropic(api_key=api_key)
        self._model = os.getenv("JARVIS_MODEL", "claude-sonnet-4-6")
        self.history: list[dict] = memory.load()

    def think(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})

        while True:
            msg = self.client.messages.create(
                model=self._model,
                max_tokens=400,
                system=SYSTEM,
                tools=_API_TOOLS_CLAUDE,
                messages=self.history,
            )
            self.history.append({"role": "assistant", "content": msg.content})

            if msg.stop_reason != "tool_use":
                reply = "".join(
                    b.text for b in msg.content if b.type == "text"
                ).strip()
                memory.save(self.history)
                return reply

            results = []
            for block in msg.content:
                if block.type != "tool_use":
                    continue
                out = _run_tool(block.name, block.input)
                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": out,
                })
            self.history.append({"role": "user", "content": results})


# ── Dışarıya açılan fabrika ────────────────────────────────────────────────
def Brain():
    if PROVIDER == "claude":
        print("[brain] Beyin: Claude")
        return _ClaudeBrain()
    print("[brain] Beyin: Gemini")
    return _GeminiBrain()
