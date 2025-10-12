# 📊 MM TRADING BOT PRO

CoinMarketCap API ve Telegram entegrasyonlu, profesyonel kripto para analiz botu.

## ✨ Özellikler

- ✅ **CoinMarketCap Entegrasyonu**: Gerçek zamanlı kripto para verileri
- ✅ **Telegram Bildirimleri**: Otomatik sinyal gönderimi
- ✅ **Web Panel**: Türkçe, mobil uyumlu yönetim paneli
- ✅ **Dinamik Eşik Sistemi**: Volatiliteye göre otomatik threshold ayarlama
- ✅ **Akıllı Fiyat Formatı**: Tüm coin türleri için doğru fiyat gösterimi
- ✅ **Otomatik Analiz**: Her 60 saniyede bir otomatik tarama
- ✅ **Çoklu Coin Desteği**: 15+ popüler kripto para
- ✅ **SQLite Veritabanı**: Sinyal geçmişi takibi

## 🚀 Hızlı Başlangıç

### Web Paneli Kullanımı

1. Tarayıcınızda panele gidin
2. **Admin Token**: `cryptobot_admin_2024`
3. Panel sekmesinden:
   - Eşik değerini ayarlayın (varsayılan: 75%)
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

1. **Veri Toplama**: CoinMarketCap'ten seçili coinlerin verilerini çeker
2. **Analiz**: 1 saatlik ve 24 saatlik değişim oranlarını analiz eder
3. **Sinyal**: Threshold'u aşan coinler için LONG/SHORT sinyali üretir
4. **Bildirim**: Telegram grubuna otomatik bildirim gönderir
5. **Kayıt**: Tüm sinyaller veritabanında saklanır

## 🛠 Teknik Detaylar

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
