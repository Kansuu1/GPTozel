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


def predict_signal_from_features(features, timeframe="24h", indicators=None):
    """
    RSI, MACD, EMA ve Combined Signal Strength ile geliştirilmiş sinyal üretimi
    
    Parametreler:
    - features: CoinMarketCap'ten gelen özellikler
    - timeframe: Analiz zaman dilimi
    - indicators: RSI, MACD, EMA ve signal_strength dict
    
    Return: (signal_type, probability, tp, sl, weight_desc)
    """
    
    # Temel momentum skoru (eski sistem)
    timeframe_mapping = {
        "15m": "percent_change_1h",
        "1h": "percent_change_1h",
        "4h": "percent_change_24h",
        "12h": "percent_change_24h",
        "24h": "percent_change_24h",
        "1d": "percent_change_24h",
        "7d": "percent_change_7d",
        "1w": "percent_change_7d",
        "30d": "percent_change_30d",
        "1m": "percent_change_30d"
    }
    
    main_key = timeframe_mapping.get(timeframe, "percent_change_24h")
    short_term = features.get("percent_change_1h") or 0.0
    main_change = features.get(main_key) or 0.0
    
    # Momentum skoru
    if timeframe in ["15m", "1h"]:
        momentum_score = main_change
    elif timeframe in ["4h", "12h"]:
        momentum_score = main_change * 0.7 + short_term * 0.3
    elif timeframe in ["24h", "1d"]:
        momentum_score = main_change * 0.8 + short_term * 0.2
    elif timeframe in ["7d", "1w"]:
        momentum_score = main_change
    else:
        momentum_score = main_change
    
    # Yeni: Combined Signal Strength bazlı probability
    if indicators and indicators.get('signal_strength'):
        signal_strength = indicators['signal_strength']
        strength_score = signal_strength.get('score', 0)
        direction = signal_strength.get('direction', 'NEUTRAL')
        
        # Signal strength ana faktör (70%)
        # Momentum destek faktör (30%)
        base_prob = strength_score * 0.7 + abs(momentum_score) * 0.3
        
        # Yön belirleme
        if direction == 'BULLISH':
            signal_type = "LONG"
            prob = base_prob
        elif direction == 'BEARISH':
            signal_type = "SHORT"
            prob = base_prob
        else:  # NEUTRAL
            # Momentum'a göre karar ver
            if abs(momentum_score) < 0.5:
                return None, 0.0, None, None, "Neutral market"
            signal_type = "LONG" if momentum_score > 0 else "SHORT"
            prob = abs(momentum_score) * 2  # Momentum'u artır
        
        weight_desc = f"Signal Strength: {strength_score:.0f}%, Direction: {direction}"
        
    else:
        # Indicators yoksa eski sistem
        prob = min(max(abs(momentum_score), 0.0), 100.0)
        
        if prob < 0.5:
            return None, prob, None, None, "Low momentum"
        
        signal_type = "LONG" if momentum_score > 0 else "SHORT"
        weight_desc = f"Momentum only: {momentum_score:.2f}%"
    
    # Minimum threshold
    if prob < 0.1:
        return None, prob, None, None, weight_desc
    
    current_price = features.get("price", 0)
    tp, sl = calculate_tp_sl(signal_type, current_price, prob)
    
    return signal_type, prob, tp, sl, weight_desc