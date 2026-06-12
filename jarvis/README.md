# JARVIS — Sesli Asistan + Minecraft Botu

PC'ni yönetebilen ve seninle Minecraft (Java Edition) oynayabilen sesli yapay zekâ asistanı.

```
🎤 Sesin ──► Whisper (STT) ──► Claude (beyin) ──► edge-tts (ses) ──► 🔊
                                     │
                          ┌──────────┴──────────┐
                          ▼                     ▼
                    PC Araçları           Minecraft Botu
                  (program aç,           (Mineflayer, WebSocket)
                   ses, ekran...)            🎮 oyuna girer
```

## Parçalar

| Dosya | Görev |
|-------|-------|
| `jarvis.py` | Ana döngü: dinle → düşün → konuş |
| `brain.py` | Claude + tool calling (karar verir) |
| `voice.py` | Mikrofon (Whisper) + sesli cevap (edge-tts) |
| `pc_tools.py` | Bilgisayar kontrolü (program aç, ses, ekran görüntüsü...) |
| `mc_bridge.py` | Python ↔ Minecraft botu köprüsü (WebSocket istemcisi) |
| `bot.js` | Mineflayer botu — oyuna girer, komutları uygular |

## Kurulum

### 1. Gereksinimler
- **Python 3.10+**
- **Node.js 18+**
- **Minecraft Java Edition** (Bedrock/telefon sürümü ÇALIŞMAZ)
- **Claude API anahtarı** → https://console.anthropic.com

### 2. Python tarafı
```bash
cd jarvis
pip install -r requirements.txt
```

### 3. Minecraft botu tarafı
```bash
cd jarvis
npm install
```

### 4. API anahtarı
`.env` dosyası oluştur (örnek: `.env.example`):
```
ANTHROPIC_API_KEY=sk-ant-...
```

## Çalıştırma

### A) Sadece sesli asistan + PC kontrolü
```bash
python jarvis.py
```
Konuşmak için **Enter**'a bas, konuş, tekrar **Enter**. (bas-konuş)

### B) Minecraft ile birlikte
1. Minecraft Java'yı aç → **Singleplayer dünya aç → ESC → "LAN'a Aç"** (Open to LAN). Çıkan port numarasını not al.
2. Botu başlat (LAN portunu gir):
   ```bash
   node bot.js --host localhost --port <LAN_PORTU>
   ```
3. Ayrı terminalde asistanı başlat:
   ```bash
   python jarvis.py
   ```
4. "Jarvis, yanıma gel", "ağaç kes", "beni takip et" de.

## Minecraft komutları (bot becerileri)
`gel`, `takip et`, `dur`, `ağaç kes`, `madde topla`, `saldır`, `nerelisin/durum`, `söyle`

## ⚠️ Notlar
- Bot ekranı **görmez**, sunucu verisinden dünyayı "bilir".
- Java Edition şart, Bedrock desteklenmez.
- PC araçları varsayılan olarak güvenli işlemlerle sınırlıdır (`pc_tools.py` içinde genişletebilirsin).
