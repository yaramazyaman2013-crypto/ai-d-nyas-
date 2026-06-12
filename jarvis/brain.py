"""Jarvis'in beyni: Claude veya Gemini ile düşünür, araçları (tool) çağırır.

Hangi beyin kullanılacağı JARVIS_PROVIDER ortam değişkeniyle seçilir:
  JARVIS_PROVIDER=claude  → Anthropic Claude (ANTHROPIC_API_KEY gerekir)
  JARVIS_PROVIDER=gemini  → Google Gemini   (GEMINI_API_KEY gerekir)  ← varsayılan
"""
import json
import os

import mc_bridge
import pc_tools

PROVIDER = os.getenv("JARVIS_PROVIDER", "gemini").lower()

SYSTEM = (
    "Sen Jarvis'sin — kullanıcının kişisel sesli asistanı. Türkçe, kısa ve "
    "samimi konuş; gereksiz uzatma. Kullanıcı bilgisayarını kontrol etmeni "
    "(program açma, ses, arama) veya Minecraft'ta bir şey yapmanı isteyebilir. "
    "Uygun aracı çağır, sonra sonucu tek-iki cümleyle sözlü olarak özetle. "
    "Araç çağırman gerekmiyorsa sadece sohbet et. Cevapların sesli okunacağı "
    "için emoji ve madde işareti kullanma."
)

_ALL_TOOLS = pc_tools.TOOLS + mc_bridge.TOOLS
_FN_MAP = {t["name"]: t["_fn"] for t in _ALL_TOOLS}
_API_TOOLS_CLAUDE = [{k: v for k, v in t.items() if k != "_fn"} for t in _ALL_TOOLS]


# ── Gemini ─────────────────────────────────────────────────────────────────
def _gemini_tools_schema():
    """Gemini function declaration formatına çevirir."""
    decls = []
    for t in _ALL_TOOLS:
        schema = dict(t["input_schema"])
        schema.pop("$schema", None)
        decls.append({
            "name": t["name"],
            "description": t["description"],
            "parameters": schema,
        })
    return [{"function_declarations": decls}]


class _GeminiBrain:
    def __init__(self):
        import google.generativeai as genai  # pip install google-generativeai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY ortam değişkeni eksik. "
                               ".env dosyasına ekle.")
        genai.configure(api_key=api_key)
        model_name = os.getenv("JARVIS_MODEL", "gemini-2.0-flash")
        self._model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM,
            tools=_gemini_tools_schema(),
        )
        self._chat = self._model.start_chat()

    def think(self, user_text: str) -> str:
        import google.generativeai as genai

        response = self._chat.send_message(user_text)

        # Araç çağırma döngüsü
        while True:
            # Araç çağrısı var mı?
            fn_calls = []
            for part in response.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    fn_calls.append(part.function_call)

            if not fn_calls:
                # Düz metin cevabı
                return response.text.strip()

            # Araçları çalıştır ve sonuçları geri ver
            results = []
            for call in fn_calls:
                fn = _FN_MAP.get(call.name)
                kwargs = dict(call.args)
                try:
                    out = fn(**kwargs) if fn else f"Bilinmeyen araç: {call.name}"
                except Exception as e:
                    out = f"Araç hatası ({call.name}): {e}"
                print(f"   🔧 {call.name}({dict(call.args)}) → {out}")
                results.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
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
            raise RuntimeError("ANTHROPIC_API_KEY ortam değişkeni eksik. "
                               ".env dosyasına ekle.")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.history: list[dict] = []
        self._model = os.getenv("JARVIS_MODEL", "claude-sonnet-4-6")

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
                return "".join(
                    b.text for b in msg.content if b.type == "text"
                ).strip()

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


# ── Dışarıya açılan sınıf ──────────────────────────────────────────────────
def Brain():
    """JARVIS_PROVIDER'a göre doğru beyin nesnesini döndürür."""
    if PROVIDER == "claude":
        print("[brain] Beyin: Claude")
        return _ClaudeBrain()
    print("[brain] Beyin: Gemini")
    return _GeminiBrain()
