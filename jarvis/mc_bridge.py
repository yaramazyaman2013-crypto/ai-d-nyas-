"""Minecraft köprüsü: Python beyni ile Mineflayer botu (bot.js) arasındaki hat.

bot.js bir WebSocket SUNUCUSU çalıştırır. Burası ona İSTEMCİ olarak bağlanır,
JSON komut gönderir {"action": "...", "params": {...}} ve cevabı bekler.

Bot çalışmıyorsa araçlar nazikçe "bot bağlı değil" der — asistan yine de çalışır.
"""
import asyncio
import json
import os

try:
    import websockets
except ImportError:  # asistan botsuz da çalışsın
    websockets = None

BRIDGE_URL = os.getenv("JARVIS_MC_BRIDGE", "ws://localhost:8765")


def _send(action: str, params: dict | None = None) -> str:
    """Bota tek komut gönderip cevabını döndürür (senkron sarmalayıcı)."""
    if websockets is None:
        return "Minecraft köprüsü için 'websockets' kurulu değil."

    async def _go():
        try:
            async with websockets.connect(BRIDGE_URL, open_timeout=3) as ws:
                await ws.send(json.dumps({"action": action,
                                          "params": params or {}}))
                reply = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(reply)
                return data.get("message", "Tamam.")
        except (OSError, asyncio.TimeoutError):
            return ("Minecraft botuna ulaşamadım — bot.js çalışıyor ve oyuna "
                    "girmiş mi kontrol et.")
        except Exception as e:
            return f"Minecraft komutu hata verdi: {e}"

    return asyncio.run(_go())


# ── Bota gönderilen yetenekler ────────────────────────────────────────────
def mc_come(**_) -> str:
    return _send("come")


def mc_follow(**_) -> str:
    return _send("follow")


def mc_stop(**_) -> str:
    return _send("stop")


def mc_chop_tree(adet: int = 1, **_) -> str:
    return _send("chop_tree", {"count": int(adet)})


def mc_collect(blok: str, adet: int = 1, **_) -> str:
    return _send("collect", {"block": blok, "count": int(adet)})


def mc_attack(**_) -> str:
    return _send("attack")


def mc_status(**_) -> str:
    return _send("status")


def mc_say(mesaj: str, **_) -> str:
    return _send("say", {"text": mesaj})


TOOLS = [
    {
        "_fn": mc_come,
        "name": "mc_come",
        "description": "Minecraft botu oyuncunun yanına gelir.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "_fn": mc_follow,
        "name": "mc_follow",
        "description": "Bot oyuncuyu takip etmeye başlar.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "_fn": mc_stop,
        "name": "mc_stop",
        "description": "Bot ne yapıyorsa durur.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "_fn": mc_chop_tree,
        "name": "mc_chop_tree",
        "description": "Bot en yakın ağaçları keser ve odun toplar.",
        "input_schema": {
            "type": "object",
            "properties": {"adet": {"type": "integer", "description": "kaç blok odun"}},
        },
    },
    {
        "_fn": mc_collect,
        "name": "mc_collect",
        "description": "Belirtilen blok türünü toplar (örn. dirt, stone, coal_ore).",
        "input_schema": {
            "type": "object",
            "properties": {
                "blok": {"type": "string"},
                "adet": {"type": "integer"},
            },
            "required": ["blok"],
        },
    },
    {
        "_fn": mc_attack,
        "name": "mc_attack",
        "description": "Bot en yakın düşman/canavara saldırır.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "_fn": mc_status,
        "name": "mc_status",
        "description": "Botun canı, açlığı, konumu ve envanterini bildirir.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "_fn": mc_say,
        "name": "mc_say",
        "description": "Bot oyun içi sohbete mesaj yazar.",
        "input_schema": {
            "type": "object",
            "properties": {"mesaj": {"type": "string"}},
            "required": ["mesaj"],
        },
    },
]
