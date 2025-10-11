# backend/model_stub.py
# This is current "model" - a rule-based stub. Replace with XGBoost/LightGBM later.

def calculate_tp_sl(signal_type: str, current_price: float, probability: float):
    """
    TP (Take Profit) ve SL (Stop Loss) hesaplama
    
    Parametreler:
    - signal_type: "LONG" veya "SHORT"
    - current_price: Mevcut fiyat
    - probability: Sinyal güvenilirliği (0-100)
    
    Risk Yönetimi:
    - SL: %2-5 arası (güvenilirlik düştükçe artar)
    - TP: Risk/Reward 1:2 veya 1:3 (güvenilirlik arttıkça artar)
    """
    if not current_price or current_price <= 0:
        return None, None
    
    # Güvenilirliğe göre dinamik risk yüzdesi
    # Yüksek güvenilirlik = düşük SL, yüksek TP
    if probability >= 20:
        sl_percent = 3.0  # %3 stop loss
        risk_reward = 3.0  # 1:3 risk/reward
    elif probability >= 10:
        sl_percent = 4.0  # %4 stop loss
        risk_reward = 2.5  # 1:2.5 risk/reward
    else:
        sl_percent = 5.0  # %5 stop loss
        risk_reward = 2.0  # 1:2 risk/reward
    
    tp_percent = sl_percent * risk_reward
    
    if signal_type == "LONG":
        # LONG: Fiyat yükselecek
        stop_loss = current_price * (1 - sl_percent / 100)
        take_profit = current_price * (1 + tp_percent / 100)
    else:  # SHORT
        # SHORT: Fiyat düşecek
        stop_loss = current_price * (1 + sl_percent / 100)
        take_profit = current_price * (1 - tp_percent / 100)
    
    return round(take_profit, 8), round(stop_loss, 8)


def predict_signal_from_features(features, timeframe="24h"):
    """
    Seçilen timeframe'e göre sinyal üretir
    
    Parametreler:
    - features: CoinMarketCap'ten gelen özellikler
    - timeframe: Analiz zaman dilimi (15m, 1h, 4h, 12h, 24h, 7d)
    
    Return: (signal_type, probability, tp, sl)
    """
    
    # Timeframe'e göre doğru değişim oranını seç
    timeframe_mapping = {
        "15m": "percent_change_1h",    # 15m için 1h kullan (en yakın)
        "1h": "percent_change_1h",
        "4h": "percent_change_24h",     # 4h için 24h kullan
        "12h": "percent_change_24h",    # 12h için 24h kullan
        "24h": "percent_change_24h",
        "1d": "percent_change_24h",     # Alternatif gösterim
        "7d": "percent_change_7d",
        "1w": "percent_change_7d",      # Alternatif gösterim
        "30d": "percent_change_30d",
        "1m": "percent_change_30d"      # 1 ay alternatif gösterim
    }
    
    # Ana ve yardımcı timeframe'ler
    main_key = timeframe_mapping.get(timeframe, "percent_change_24h")
    
    # Kısa vadeli momentum için 1h her zaman kontrol edilir
    short_term = features.get("percent_change_1h") or 0.0
    main_change = features.get(main_key) or 0.0
    
    # Timeframe'e göre ağırlıklandırma
    if timeframe in ["15m", "1h"]:
        # Kısa vade: sadece 1h önemli
        score = main_change
        weight_desc = "1h momentum"
    elif timeframe in ["4h", "12h"]:
        # Orta vade: 24h ana, 1h destek
        score = main_change * 0.7 + short_term * 0.3
        weight_desc = "24h (70%) + 1h (30%)"
    elif timeframe in ["24h", "1d"]:
        # Günlük: 24h ana, 1h destek
        score = main_change * 0.8 + short_term * 0.2
        weight_desc = "24h (80%) + 1h (20%)"
    else:  # 7d, 1w
        # Haftalık: sadece 7d
        score = main_change
        weight_desc = "7d trend"
    
    prob = min(max(abs(score), 0.0), 100.0)
    
    if prob < 0.5:
        return None, prob, None, None, weight_desc
    
    current_price = features.get("price", 0)
    
    if score > 0:
        signal_type = "LONG"
    else:
        signal_type = "SHORT"
    
    tp, sl = calculate_tp_sl(signal_type, current_price, prob)
    
    return signal_type, prob, tp, sl, weight_desc