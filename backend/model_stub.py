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


def predict_signal_from_features(features):
    """
    Return tuple (signal_type:str or None, probability:float)
    probability scale: 0..100 (percentage)
    """
    # Simple rule:
    pc24 = features.get("percent_change_24h") or 0.0
    pc1h = features.get("percent_change_1h") or 0.0
    score = pc24 * 0.5 + pc1h * 0.5  # naive blend
    prob = min(max(abs(score), 0.0), 100.0)
    if prob < 0.5:
        return None, prob, None, None
    
    current_price = features.get("price", 0)
    
    if score > 0:
        signal_type = "LONG"
    else:
        signal_type = "SHORT"
    
    tp, sl = calculate_tp_sl(signal_type, current_price, prob)
    
    return signal_type, prob, tp, sl