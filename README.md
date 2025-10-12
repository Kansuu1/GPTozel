# 📊 MM TRADING BOT PRO

CoinMarketCap API ve Telegram entegrasyonlu, profesyonel kripto para analiz botu.

## ✨ Özellikler

- ✅ **CoinMarketCap Entegrasyonu**: Gerçek zamanlı kripto para verileri
- ✅ **Telegram Bildirimleri**: Otomatik sinyal gönderimi
- ✅ **Web Panel**: Türkçe, mobil uyumlu yönetim paneli
- ✅ **Coin Başına Özel Ayarlar**: Her coin için ayrı timeframe, eşik ve mod
- ✅ **Dinamik Eşik Sistemi**: Volatiliteye göre otomatik threshold ayarlama
- ✅ **Akıllı Fiyat Formatı**: Tüm coin türleri için doğru fiyat gösterimi
- ✅ **Otomatik Analiz**: Her 60 saniyede bir otomatik tarama
- ✅ **Çoklu Coin Desteği**: 15+ popüler kripto para
- ✅ **SQLite Veritabanı**: Sinyal geçmişi takibi
- ✅ **Coin Başına Fetch Interval**: Her coin için ayrı veri çekme aralığı (dakika)
- ✅ **Active/Passive Status**: Pasif coinler API kotası harcamaz
- ✅ **Gerçek Zamanlı Güncelleme**: Son veri çekme zamanı gösterimi

## 🚀 Hızlı Başlangıç

### Web Paneli Kullanımı

1. Tarayıcınızda panele gidin
2. **Admin Token**: Token'ınızı girin
3. Panel sekmesinden:
   - **Eşik Tipi** seçin:
     - **Manuel**: Sabit eşik değeri kullanır
     - **Dinamik**: Volatiliteye göre otomatik eşik hesaplar
   - Eşik değerini ayarlayın (manuel mod için)
   - Zaman dilimi seçin (15m - 30d)
   - Analiz edilecek coinleri seçin
   - "Ayarları Kaydet" butonuna tıklayın
4. "Telegram Test" ile bağlantıyı test edin
5. "Şimdi Analiz Et" ile manuel analiz başlatın

### API Kullanımı

```bash
# API durumu
curl http://localhost:8001/api/

# Telegram test
curl -X POST http://localhost:8001/api/test_telegram \
  -H "x-admin-token: cryptobot_admin_2024"

# Manuel analiz
curl -X POST http://localhost:8001/api/analyze_now \
  -H "x-admin-token: cryptobot_admin_2024"

# Sinyalleri görüntüle
curl http://localhost:8001/api/signals?limit=20
```

## 📊 Nasıl Çalışır?



## 🎯 Dinamik Eşik Sistemi

### Nasıl Çalışır?

**Manuel Mod:**
- Sabit threshold değeri kullanılır
- Tüm coinler için aynı eşik uygulanır
- Örnek: %4 threshold → Sadece %4+ sinyaller gönderilir

**Dinamik Mod:**
- Her coin için volatilite hesaplanır
- Volatiliteye göre otomatik threshold belirlenir
- Timeframe'e göre optimize edilir

### Volatilite Bazlı Threshold

| Volatilite | Threshold (24h) | Açıklama |
|------------|----------------|----------|
| >15% | 8.0% | Çok yüksek volatilite - çok seçici |
| 10-15% | 5.0% | Yüksek volatilite - seçici |
| 7-10% | 3.5% | Orta-yüksek volatilite |
| 5-7% | 2.5% | Orta volatilite |
| 3-5% | 1.5% | Orta-düşük volatilite |
| 1-3% | 1.0% | Düşük volatilite |
| <1% | 0.5% | Çok düşük volatilite - hassas |

### Timeframe Çarpanları

| Timeframe | Çarpan | Örnek (vol=5%) |
|-----------|--------|----------------|
| 15m, 1h | 0.7-0.8x | 1.75-2.0% |
| 4h, 12h, 24h | 1.0x | 2.5% |
| 7d, 30d | 1.2-1.3x | 3.0-3.25% |

### Örnek Senaryolar

**PEPE (Yüksek Volatilite):**
- Volatilite: ~10%
- Dinamik Threshold (24h): 5.0%
- Sonuç: Sadece güçlü sinyaller geçer ✅

**BTC (Düşük Volatilite):**
- Volatilite: ~2%
- Dinamik Threshold (24h): 1.0%
- Sonuç: Erken sinyaller yakalanır ✅

1. **Veri Toplama**: CoinMarketCap'ten seçili coinlerin verilerini çeker
2. **Analiz**: 1 saatlik ve 24 saatlik değişim oranlarını analiz eder
3. **Sinyal**: Threshold'u aşan coinler için LONG/SHORT sinyali üretir
4. **Bildirim**: Telegram grubuna otomatik bildirim gönderir
5. **Kayıt**: Tüm sinyaller veritabanında saklanır

## 🛠 Teknik Detaylar


## ⚙️ Coin Başına Özel Ayarlar

### Nasıl Kullanılır?

**1. Modu Seçin:**
- Web panelinde "Sinyal Ayarları" kartında toggle butonunu kullanın
- ✅ **Coin Başına Özel Ayarlar Aktif**: Her coin kendi ayarlarıyla analiz edilir
- ⚙️ **Global Ayarlar Aktif**: Tüm coinler aynı ayarlarla analiz edilir

**2. Coin Ayarlarını Yapın** (Coin-bazlı mod aktifken):
- "Coin Başına Özel Ayarlar" kartı görünür
- Her coin için:
  - **Zaman Dilimi**: 15m, 1h, 4h, 12h, 24h, 7d, 30d
  - **Eşik (%)**: Manuel threshold değeri
  - **Mod**: Manuel veya Dinamik
  - **Sil Butonu** (🗑️): Coin'i listeden çıkar

**3. Coin Ekleme/Çıkarma:**
- **Yeni Coin Ekle**: Alt kısımda input ve "➕ Ekle" butonu
- Coin sembolü girin (örn: ADA, DOGE, XRP)
- Enter veya "Ekle" butonuyla listeye ekleyin
- Varsayılan ayarlarla eklenir, sonra özelleştirebilirsiniz
- **Sil**: Her coin satırında 🗑️ butonu ile çıkarabilirsiniz
- Değişiklikleri kaydetmeyi unutmayın!


### Mod Karşılaştırması

| Özellik | Global Mod | Coin-Bazlı Mod |
|---------|-----------|----------------|
| Timeframe | Tek (tüm coinler için) | Her coin için ayrı |
| Threshold | Tek | Her coin için ayrı |
| Dinamik/Manuel | Tek | Her coin için ayrı |
| Kullanım | Basit, hızlı | Optimize, hassas |
| Önerilen | Başlangıç | İleri seviye |

### Örnekler

**Global Mod Örneği:**
```
Ayar: timeframe=24h, threshold=4%, mode=dynamic
Sonuç: 
  - BTC → 24h, 4%
  - ETH → 24h, 4%
  - PEPE → 24h, 4%
  (Tüm coinler aynı ayarla analiz edilir)
```

**Coin-Bazlı Mod Örneği:**
```
Ayarlar:
  - BTC: timeframe=1h, threshold=3%, mode=dynamic
  - ETH: timeframe=1h, threshold=3%, mode=dynamic
  - PEPE: timeframe=15m, threshold=6%, mode=dynamic

Sonuç:
  - BTC → 1h analiz, düşük threshold
  - ETH → 1h analiz, düşük threshold
  - PEPE → 15m hızlı analiz, yüksek threshold
  (Her coin optimize ayarlarla analiz edilir)
```

**3. Önemli:**
- Coin-bazlı mod aktifken global ayarlar otomatik devre dışı kalır
- Global moda dönüldüğünde tüm coinler aynı ayarları kullanır

### Örnek Konfigürasyon

| Coin | Timeframe | Eşik | Mod | Açıklama |
|------|-----------|------|-----|----------|
| BTC | 1h | 3.0% | Dinamik | Saatlik analiz, düşük threshold |
| ETH | 1h | 3.0% | Dinamik | Saatlik analiz |
| SOL | 15m | 5.0% | Dinamik | Hızlı sinyaller, orta threshold |
| PEPE | 15m | 6.0% | Dinamik | Yüksek volatilite, yüksek threshold |
| TRUMP | 4h | 4.0% | Manuel | 4 saatlik analiz, sabit threshold |
| COAI | 24h | 3.0% | Dinamik | Günlük trend takibi |

### Öneriler

**Düşük Volatilite Coinler (BTC, ETH):**
- Timeframe: 1h - 4h
- Threshold: 2-3%
- Mod: Dinamik

**Orta Volatilite (SOL, ADA):**
- Timeframe: 15m - 1h
- Threshold: 4-5%
- Mod: Dinamik

**Yüksek Volatilite (PEPE, SHIB):**
- Timeframe: 15m
- Threshold: 5-7%
- Mod: Dinamik (daha seçici)

### Avantajlar

✅ Her coin'in trading tarzına göre optimize edilmiş sinyaller
✅ Gereksiz sinyaller azalır
✅ Doğruluk oranı artar
✅ Coin bazlı risk yönetimi


- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: React + Axios
- **Entegrasyonlar**: CoinMarketCap API + Telegram Bot API
- **Otomatik Analiz**: Her 60 saniyede bir çalışır

## 📱 Telegram Ayarları

Bot token'ınız ve chat ID'niz `.env` dosyasında tanımlı:
- Bot Token: `8489964512:AAGTLTRkv9VKK1fy9Mb6nvGSlKsuYxoPMRM`
- Chat ID: `-1003097160408`

## 🔧 Özelleştirme

### Threshold Değiştirme
Web panelinden "Eşik Değeri" alanını değiştirin.

### Coin Listesi
Web panelinden istediğiniz coinleri seçin/kaldırın.

## 🐛 Sorun Giderme

### Backend logları
```bash
tail -f /var/log/supervisor/backend.out.log
```

### Frontend logları
```bash
tail -f /var/log/supervisor/frontend.out.log
```

### Servisleri yeniden başlatma
```bash
sudo supervisorctl restart all
```

## ⚠️ Önemli Notlar

- Bot her 60 saniyede bir otomatik analiz yapar
- Sadece threshold'u aşan sinyaller gönderilir
- Finansal tavsiye içermez, yatırım kararlarınızı kendi sorumluluğunuzda verin

## 📈 Gelecek Geliştirmeler

- Gelişmiş teknik analiz göstergeleri (RSI, MACD)
- Machine Learning modeli
- Grafiksel görselleştirme
- Portfolio takibi
- Fiyat alarmları

---

**Made with ❤️ for Crypto Traders**
