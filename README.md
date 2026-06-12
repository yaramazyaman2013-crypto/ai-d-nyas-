# 🤖 JARVIS — Sesli Yapay Zekâ Asistanı + Minecraft Botu

Bilgisayarını sesle yönetebilen ve seninle **Minecraft (Java Edition)** oynayabilen Türkçe bir yapay zekâ asistanı. Konuşursun, Jarvis anlar, yapar ve sana sesli cevap verir.

```
🎤 Sesin ─► Whisper (anlama) ─► Gemini/Claude (beyin) ─► edge-tts (konuşma) ─► 🔊
                                       │
                          ┌────────────┴────────────┐
                          ▼                          ▼
                    💻 PC Kontrolü            🎮 Minecraft Botu
              (program aç, ses, medya,      (gel, ağaç kes, craft,
               ekran, kilitle...)            madden kaz, savaş...)
```

> Tüm kod `jarvis/` klasöründedir.

---

## 📋 Çalıştırmak için gerekenler

Kurmadan önce bilgisayarında şunlar olmalı:

| Gereksinim | Ne işe yarar | Nereden |
|-----------|--------------|---------|
| **Python 3.10+** | Asistanın beyni | https://www.python.org/downloads (kurulumda **"Add Python to PATH"** kutusunu işaretle!) |
| **Node.js 18+** | Minecraft botu için (opsiyonel) | https://nodejs.org |
| **Minecraft Java Edition** | Oyun (opsiyonel) | https://www.minecraft.net — ⚠️ Bedrock/telefon sürümü ÇALIŞMAZ |
| **Gemini API anahtarı** | Yapay zekâ beyni (ücretsiz) | https://aistudio.google.com/apikey |
| **Mikrofon + hoparlör** | Sesli konuşma | — |

> Sadece sesli asistan istiyorsan Node.js ve Minecraft'a gerek yok.

---

## 🚀 Kurulum (3 adım)

### 1) Projeyi indir
GitHub'da yeşil **"Code"** butonuna tıkla → **"Download ZIP"** → çıkart.
(Veya `git clone https://github.com/yaramazyaman2013-crypto/ai-d-nyas-.git`)

### 2) Başlat
`jarvis` klasörünü aç ve:

- **Windows:** `baslat.bat` dosyasına **çift tıkla**
- **Mac/Linux:** terminalde `bash baslat.sh`

İlk çalıştırmada **gerekli her şeyi (Python kütüphaneleri + bot paketleri) kendisi otomatik kurar**. Birkaç dakika sürebilir, bekle.

### 3) API anahtarını gir
İlk açılışta anahtar ister:
```
Gemini API anahtarını gir: ____
```
https://aistudio.google.com/apikey adresinden ücretsiz anahtar al, yapıştır, **Enter**. Bir kez kaydedilir, bir daha sormaz.

✅ Hazır! Jarvis "Merhaba, ben Jarvis. Emrindeyim." diyecek.

---

## 🎙️ Nasıl konuşulur

İki mod var:

**Sürekli dinleme (varsayılan)** — `baslat.bat`
> Hiçbir tuşa basmadan **"Jarvis"** de → o uyanır ve seni dinler. Enter gerekmez.

**Bas-konuş** — `baslat.bat --enter`
> ENTER'a bas → konuş → ENTER'a bas → Jarvis cevaplar.

### Komutlar serbest — kelimesi kelimesine söylemen gerekmez
Jarvis ne demek istediğini anlar. Örnekler:
- "Jarvis, Chrome'u açsana"
- "Sesi biraz kıs"
- "Şu müziği durdur artık"
- "Saat kaç acaba?"
- "Bilgisayarı kilitle"
- Minecraft: "bize biraz kömür lazım", "şuraya güzel bir ev kondur", "yanıma gelsene"

---

## 🎮 Minecraft ile oynamak

1. Minecraft Java Edition'da bir dünya aç.
2. **ESC → "LAN'a Aç" (Open to LAN)** → çıkan **port numarasını** not al (örn. 25565).
3. `jarvis` klasöründe yeni bir terminal aç ve botu başlat:
   ```bash
   node bot.js --host localhost --port BURAYA_PORT
   ```
   Oyuna "Jarvis" adında bir oyuncu girer.
4. Asistanı çalıştır (`baslat.bat`) ve konuş:
   - "Jarvis, yanıma gel"
   - "Beni takip et"
   - "Ağaç kes"
   - "Taş kaz"
   - "Kılıç yap" (craft)
   - "Yemek ye"
   - "Envanterinde ne var?"

> Bot canı azalınca otomatik yemek yer.

---

## 🔑 Claude kullanmak istersen (Gemini yerine)

`jarvis/.env` dosyasını aç ve şunu yaz:
```
JARVIS_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
JARVIS_MODEL=claude-sonnet-4-6
```
Anahtarı https://console.anthropic.com adresinden alırsın.

---

## ❓ Sık karşılaşılan sorunlar

| Sorun | Çözüm |
|-------|-------|
| **Pencere açılıp hemen kapanıyor** | `jarvis.py` yerine **`baslat.bat`**'a çift tıkla — hata ekranda kalır |
| **"python bulunamadı"** | Python'u kurarken "Add Python to PATH" kutusunu işaretlemedin. Tekrar kur. |
| **Ses gelmiyor / mikrofon çalışmıyor** | Mikrofon izinlerini ve Windows ses ayarlarını kontrol et |
| **Bot oyuna giremiyor** | Minecraft **Java** mı? "LAN'a Aç" yaptın mı? Port doğru mu? |
| **Bot Minecraft sürümüyle uyumsuz** | `npm install minecraft-data@latest` çalıştır |

Hata mesajını paylaşırsan çözmeye yardım ederiz.

---

## 🛠️ Teknik özet

| Katman | Teknoloji |
|--------|-----------|
| Konuşma tanıma (STT) | faster-whisper (yerel, ücretsiz) |
| Beyin (LLM) | Google Gemini veya Anthropic Claude |
| Ses sentezi (TTS) | edge-tts (Türkçe, ücretsiz) |
| PC kontrolü | Python (cross-platform) |
| Minecraft | Mineflayer (Node.js) + WebSocket köprüsü |
| Hafıza | JSON tabanlı konuşma kaydı |

Detaylı geliştirici notları için `jarvis/README.md` dosyasına bak.
