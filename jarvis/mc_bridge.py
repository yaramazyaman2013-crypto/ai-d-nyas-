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
    {
        "_fn": lambda item="crafting_table", count=1, **_: _send("craft", {"item": item, "count": int(count)}),
        "name": "mc_craft",
        "description": "Minecraft'ta eşya yapar (craft eder). Örn. crafting_table, wooden_pickaxe, torch.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string", "description": "Yapılacak eşya adı (minecraft id, örn. wooden_pickaxe)"},
                "count": {"type": "integer"},
            },
            "required": ["item"],
        },
    },
    {
        "_fn": lambda food=None, **_: _send("eat", {"food": food} if food else {}),
        "name": "mc_eat",
        "description": "Bot envanterdeki yiyeceği yer. food parametresi opsiyonel (belirtilmezse en iyi yiyeceği seçer).",
        "input_schema": {
            "type": "object",
            "properties": {"food": {"type": "string", "description": "Yenecek yiyecek adı (opsiyonel)"}},
        },
    },
    {
        "_fn": lambda **_: _send("sleep"),
        "name": "mc_sleep",
        "description": "Bot yakındaki yatakta uyur.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "_fn": lambda **_: _send("inventory"),
        "name": "mc_inventory",
        "description": "Botun envanterini listeler.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "_fn": lambda item, count=1, **_: _send("drop", {"item": item, "count": int(count)}),
        "name": "mc_drop",
        "description": "Envanterdeki bir eşyayı yere düşürür.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["item"],
        },
    },
    {
        "_fn": lambda item, **_: _send("equip", {"item": item}),
        "name": "mc_equip",
        "description": "Bir eşyayı eline alır/kuşanır.",
        "input_schema": {
            "type": "object",
            "properties": {"item": {"type": "string"}},
            "required": ["item"],
        },
    },
    {
        "_fn": lambda block, count=1, **_: _send("mine", {"block": block, "count": int(count)}),
        "name": "mc_mine",
        "description": "Belirtilen blok türünü kazır (örn. stone, coal_ore, iron_ore, dirt).",
        "input_schema": {
            "type": "object",
            "properties": {
                "block": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["block"],
        },
    },
    {
        "_fn": lambda x, y, z, **_: _send("go_to", {"x": int(x), "y": int(y), "z": int(z)}),
        "name": "mc_go_to",
        "description": "Botu belirtilen koordinatlara gönderir.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
                "z": {"type": "integer"},
            },
            "required": ["x", "y", "z"],
        },
    },
    {
        "_fn": lambda ore="coal", amount=32, **_: _send("mine_mission", {"ore": ore, "amount": int(amount)}),
        "name": "mc_mine_mission",
        "description": (
            "Madencilik görevi: belirtilen madeni arar, kazır, oyuncuya geri döner. "
            "ore değerleri: coal, iron, gold, diamond, lapis, redstone, emerald, copper. "
            "Uygun kazma otomatik seçilir. Envanter dolunca veya görev tamamlanınca döner."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ore": {"type": "string", "description": "Maden türü: coal, iron, gold, diamond, lapis, redstone, copper"},
                "amount": {"type": "integer", "description": "Kaç maden kazılacak (varsayılan 32)"},
            },
        },
    },
    {
        "_fn": lambda yapi="kulübe", malzeme=None, **_: _send("build", {"yapi": yapi, "malzeme": malzeme}),
        "name": "mc_build",
        "description": (
            "Minecraft'ta yapı inşa eder. "
            "Bilinen yapılar: kulübe (5x5 ev), kule (3x3 15 katlı), gökdelen (7x7 30 katlı), köprü (3x20), duvar (1x10x5). "
            "Malzeme envanterde olmalı (ahşap, taş, toprak vb.). "
            "malzeme parametresi opsiyonel — belirtilmezse envanterdeki ilk uygun bloğu kullanır."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "yapi": {"type": "string", "description": "kulübe, kule, gökdelen, köprü veya duvar"},
                "malzeme": {"type": "string", "description": "Kullanılacak blok adı, örn. oak_planks, cobblestone (opsiyonel)"},
            },
            "required": ["yapi"],
        },
    },
    {
        "_fn": lambda blocks, **_: _send("build_custom", {"blocks": blocks}),
        "name": "mc_build_custom",
        "description": (
            "Özel/serbest yapı inşa eder — SEN tasarlarsın. "
            "Ev, kale, heykel, havuz, kafe gibi istediğin yapıyı kendi bilginle tasarla "
            "ve bloklarının listesini ver. blocks: bota göre relatif koordinatlardaki "
            "blok listesi [{dx, dy, dz, block}]. dx=sağ/sol, dy=yukarı/aşağı, dz=ileri. "
            "Alt katmanları küçük dy ile ver (yapı alttan üste kurulur). "
            "block alanı Minecraft blok adıdır (örn. oak_planks, cobblestone, glass, oak_door). "
            "Kullanıcı 'ev yap', 'kale yap' gibi serbest bir şey isterse bunu kullan — "
            "kendi mimari bilginle tasarla. Malzemeler botun envanterinde olmalı. "
            "Çok büyük yapılarda 200 bloğu geçme, gerekirse parça parça inşa et."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "blocks": {
                    "type": "array",
                    "description": "Yerleştirilecek bloklar (alttan üste)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "dx": {"type": "integer"},
                            "dy": {"type": "integer"},
                            "dz": {"type": "integer"},
                            "block": {"type": "string"},
                        },
                        "required": ["dx", "dy", "dz", "block"],
                    },
                },
            },
            "required": ["blocks"],
        },
    },
    {
        "_fn": lambda sure=60, **_: _send("survive", {"sure": int(sure)}),
        "name": "mc_survive",
        "description": (
            "Belirtilen süre boyunca (saniye) otomatik hayatta kalma görevi: "
            "ağaç keser, düşmanlara savaşır, acıkınca yer. Varsayılan 60 saniye."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sure": {"type": "integer", "description": "Görev süresi saniye cinsinden"},
            },
        },
    },
]
