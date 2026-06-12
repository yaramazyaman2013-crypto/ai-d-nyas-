"""Jarvis'in beyni: Groq, Claude veya Gemini ile düşünür, araçları (tool) çağırır.

Hangi beyin kullanılacağı JARVIS_PROVIDER ortam değişkeniyle seçilir:
  JARVIS_PROVIDER=groq    → Groq / Llama  (GROQ_API_KEY gerekir)  ← varsayılan, hızlı+ücretsiz
  JARVIS_PROVIDER=gemini  → Google Gemini (GEMINI_API_KEY gerekir)
  JARVIS_PROVIDER=claude  → Anthropic Claude (ANTHROPIC_API_KEY gerekir)
"""
import json
import os

import mc_bridge
import memory
import pc_tools

PROVIDER = os.getenv("JARVIS_PROVIDER", "groq").lower()

SYSTEM = """Sen Jarvis'sin — kullanıcının kişisel sesli asistanı ve Minecraft arkadaşı.
Türkçe konuş, kısa ve net cevap ver. Emoji ve madde işareti kullanma (sesli okunacak).

=== BİLGİSAYAR KOMUTLARI ===
Kullanıcı aşağıdaki gibi şeyler söylediğinde MUTLAKA araç çağır:

• "chrome aç", "tarayıcı aç", "Firefox başlat" → open_app(isim="chrome")
• "notepad aç", "hesap makinesi aç" → open_app(isim="notepad") / open_app(isim="calc")
• "YouTube aç", "YouTube'a git" → open_website(site="youtube")
• "WhatsApp aç", "mesajlarıma bak" → open_website(site="whatsapp")
• "Instagram aç" → open_website(site="instagram")
• "Gmail aç", "mail aç" → open_website(site="gmail")
• "Netflix aç" → open_website(site="netflix")
• "Spotify aç" → open_website(site="spotify")
• "YouTube'da lofi müzik aç", "şarkı ara" → open_youtube(sorgu="lofi müzik")
• "Google'da ara", "...yı ara" → search_web(sorgu="...")
• "... sitesini aç" → open_url(url="...")
• "sesi aç/kıs/yükselt/azalt/50 yap" → set_volume(seviye=...)
  (tam komut verilmezse: "sesi aç"=80, "biraz kıs"=40, "kıs"=30, "sessize al"=0)
• "müziği durdur/başlat/devam et" → media_control(action="play_pause")
• "sonraki şarkı/parça" → media_control(action="next")
• "önceki şarkı" → media_control(action="previous")
• "ekran görüntüsü al/screenshot" → take_screenshot()
• "saat kaç/tarih ne" → get_time()
• "hava nasıl", "İstanbul'da hava" → get_weather(sehir="İstanbul")
  (şehir belirtilmezse varsayılan "İstanbul" kullan)
• "bilgisayar nasıl", "ram doldu mu", "cpu ne kadar" → system_status()
• "bilgisayarı kilitle/ekranı kapat" → lock_screen()
• "...yı panoya kopyala" → clipboard_copy(metin="...")
• "şunu yaz" → type_text(metin="...")

=== MİNECRAFT KOMUTLARI ===
Minecraft botu bağlıysa şu araçlar kullanılabilir:

• "yanıma gel", "buradasın mı" → mc_come()
• "beni takip et/izle" → mc_follow()
• "dur/bekle" → mc_stop()
• "ağaç kes/odun topla" → mc_chop_tree()
• "eşyaları topla" → mc_collect()
• "düşmanı vur/saldır" → mc_attack()
• "durumun ne/canın kaç" → mc_status()
• "kömür kaz/getir", "demir topla", "elmas bul" → mc_mine_mission(ore="coal/iron/diamond", amount=32)
  Türkçe→İngilizce: kömür=coal, demir=iron, altın=gold, elmas=diamond, bakır=copper
• "ev yap/kulübe kur" → mc_build(yapi="kulübe") veya mc_build_custom(blocks=[...])
• "ye bir şeyler/karnın acıkmış" → mc_eat()
• "uyu/gece" → mc_sleep()
• "envanterinde ne var" → mc_inventory()
• "hayatta kal/kendini yönet" → mc_survive()

=== ÖNEMLI KURALLAR ===
1. Kullanıcı doğal konuşur, tam komut vermez. NİYETİ anla, aracı seç.
   Örnek: "biraz müzik açar mısın" → open_youtube(sorgu="müzik")
   Örnek: "hava durumuna bak" → get_weather(sehir="İstanbul")
   Örnek: "chrome'u çalıştır" → open_app(isim="chrome")
2. Birden fazla adım gerekiyorsa sırayla yap.
3. Araç gerekmeyen sorularda sadece sohbet et.
4. Önceki konuşmaları hatırlıyorsun."""

_ALL_TOOLS = pc_tools.TOOLS + mc_bridge.TOOLS
_FN_MAP = {t["name"]: t["_fn"] for t in _ALL_TOOLS}
_API_TOOLS_CLAUDE = [{k: v for k, v in t.items() if k != "_fn"} for t in _ALL_TOOLS]
# OpenAI/Groq tarzı araç şeması
_API_TOOLS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    }
    for t in _ALL_TOOLS
]


# Gemini'nin proto argümanlarını (iç içe dict/list dahil) saf Python'a çevirir.
def _to_py(value):
    if hasattr(value, "items"):          # MapComposite / dict
        return {k: _to_py(v) for k, v in value.items()}
    if isinstance(value, (str, bytes)):  # str iterable ama liste değil
        return value
    if hasattr(value, "__iter__"):       # RepeatedComposite / list
        return [_to_py(v) for v in value]
    return value


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


# Gemini model öncelik sırası: birincisi kota aşarsa sonrakine geçer
_GEMINI_FALLBACK_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]


class _GeminiBrain:
    def __init__(self):
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY ortam değişkeni eksik.")
        genai.configure(api_key=api_key)
        self._genai = genai
        self._api_key = api_key

        # .env'de model belirtilmişse onu kullan, yoksa otomatik dene
        env_model = os.getenv("JARVIS_MODEL", "")
        self._model_list = [env_model] + _GEMINI_FALLBACK_MODELS if env_model else _GEMINI_FALLBACK_MODELS
        self._model_list = list(dict.fromkeys(self._model_list))  # tekrarları kaldır

        self._model_name = None
        self._model = None
        self._chat = None

        # Çalışan modeli başlangıçta bul
        self._init_model()

        # Hafızadan geçmiş yükle
        past = memory.load()
        history = []
        for m in past:
            role = "user" if m["role"] == "user" else "model"
            history.append({"role": role, "parts": [m["content"]]})
        if self._model:
            self._chat = self._model.start_chat(history=history)
        self.history = past

    def _init_model(self, skip_models=None):
        """Çalışan bir Gemini modeli bul ve başlat."""
        skip = set(skip_models or [])
        for model_name in self._model_list:
            if model_name in skip:
                continue
            try:
                self._model = self._genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=SYSTEM,
                    tools=_gemini_tools_schema(),
                )
                self._model_name = model_name
                print(f"[brain] Gemini modeli: {model_name}")
                return
            except Exception:
                continue
        raise RuntimeError(
            "Gemini API anahtarın çalışmıyor veya tüm modeller kota aşımında.\n"
            "Çözüm:\n"
            "  1. Yeni bir API anahtarı al → https://aistudio.google.com/apikey\n"
            "  2. jarvis/.env dosyasında GEMINI_API_KEY satırını yeni anahtarla güncelle\n"
            "  3. Veya ücretsiz kota doldu ise yarın tekrar dene (günlük limit sıfırlanır)"
        )

    def think(self, user_text: str) -> str:
        self.history.append({"role": "user", "content": user_text})

        # Kota aşımında sonraki modele geçerek tekrar dene
        tried = set()
        while True:
            try:
                response = self._chat.send_message(user_text)
                break
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
                    tried.add(self._model_name)
                    remaining = [m for m in self._model_list if m not in tried]
                    if remaining:
                        print(f"[brain] {self._model_name} kotası doldu, {remaining[0]}'e geçiliyor...")
                        self._init_model(skip_models=tried)
                        past = self.history[:-1]  # son user mesajı hariç geçmiş
                        history = []
                        for m in past:
                            if isinstance(m.get("content"), str):
                                role = "user" if m["role"] == "user" else "model"
                                history.append({"role": role, "parts": [m["content"]]})
                        self._chat = self._model.start_chat(history=history)
                        continue
                    # Tüm modeller bitti
                    self.history.pop()
                    return (
                        "Gemini API kotası doldu. Yeni anahtar al: "
                        "aistudio.google.com/apikey — .env'e yaz ve Jarvis'i yeniden başlat."
                    )
                raise

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
                out = _run_tool(call.name, _to_py(call.args))
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


# ── Groq (Llama) ───────────────────────────────────────────────────────────
# Kota dolarsa sıraki modele geçer. Hepsi tool-calling destekler.
_GROQ_FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]


class _GroqBrain:
    def __init__(self):
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY ortam değişkeni eksik.")
        self.client = Groq(api_key=api_key)

        env_model = os.getenv("JARVIS_MODEL", "")
        self._models = ([env_model] if env_model else []) + _GROQ_FALLBACK_MODELS
        self._models = list(dict.fromkeys(self._models))
        self._model = self._models[0]
        print(f"[brain] Groq modeli: {self._model}")

        # Hafıza: sistem mesajı + geçmiş düz metinler
        self.messages = [{"role": "system", "content": SYSTEM}]
        for m in memory.load():
            if isinstance(m.get("content"), str):
                self.messages.append({"role": m["role"], "content": m["content"]})

    def _save(self):
        # Sadece düz metin user/assistant mesajlarını hafızaya yaz
        clean = [m for m in self.messages[1:]
                 if m.get("role") in ("user", "assistant")
                 and isinstance(m.get("content"), str) and m["content"]]
        memory.save(clean)

    def think(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        tool_fail_count = 0

        while True:
            # Araç çağırma birkaç kez bozulursa araçsız (sadece sohbet) dene
            use_tools = tool_fail_count < 3
            try:
                kwargs = dict(
                    model=self._model,
                    messages=self.messages,
                    max_tokens=600,
                    temperature=0.2,  # düşük = daha güvenilir araç çağrısı
                )
                if use_tools:
                    kwargs["tools"] = _API_TOOLS_OPENAI
                    kwargs["tool_choice"] = "auto"
                resp = self.client.chat.completions.create(**kwargs)
            except Exception as e:
                err = str(e)
                low = err.lower()

                # 1) Kota/limit → sonraki modele geç
                if ("429" in err or "rate" in low or "quota" in low) and len(self._models) > 1:
                    self._models.pop(0)
                    self._model = self._models[0]
                    print(f"[brain] Kota doldu, {self._model}'e geçiliyor...")
                    continue

                # 2) Araç çağrısı bozuldu → tekrar dene, olmazsa araçsız cevap ver
                if "failed to call a function" in low or "tool_use_failed" in low:
                    tool_fail_count += 1
                    print(f"[brain] Araç çağrısı bozuldu, tekrar deneniyor ({tool_fail_count}/3)...")
                    continue

                # 3) Kimlik doğrulama
                if "401" in err or "invalid_api_key" in low or "invalid api key" in low:
                    return ("Groq anahtarı geçersiz. console.groq.com/keys adresinden "
                            "yeni anahtar al ve .env dosyasındaki GROQ_API_KEY'i güncelle.")

                return f"Groq hatası: {err[:140]}"

            msg = resp.choices[0].message

            if not msg.tool_calls:
                reply = (msg.content or "").strip()
                if reply:
                    self.messages.append({"role": "assistant", "content": reply})
                    self._save()
                return reply or "Anlayamadım, tekrar söyler misin?"

            # Araç çağrılarını çalıştır
            self.messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name,
                                     "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                out = _run_tool(tc.function.name, args)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": out,
                })


# ── Dışarıya açılan fabrika ────────────────────────────────────────────────
def Brain():
    if PROVIDER == "claude":
        print("[brain] Beyin: Claude")
        return _ClaudeBrain()
    if PROVIDER == "gemini":
        print("[brain] Beyin: Gemini")
        return _GeminiBrain()
    print("[brain] Beyin: Groq")
    return _GroqBrain()
