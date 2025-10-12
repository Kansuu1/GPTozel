# backend/volatility_calculator.py
"""
Dinamik Eşik (Dynamic Threshold) Sistemi
Piyasa volatilitesine göre otomatik threshold belirleme
"""
import logging

logger = logging.getLogger(__name__)


def calculate_volatility(features: dict) -> float:
    """
    Coin'in volatilitesini hesaplar
    
    Volatilite Metriği:
    - 1h, 24h, 7d değişim oranlarının mutlak değerlerinin ortalaması
    - Yüksek volatilite = Büyük fiyat dalgalanmaları
    - Düşük volatilite = Stabil fiyat hareketi
    
    Returns:
        float: Volatilite değeri (0-100 arası)
    """
    try:
        # Farklı zaman dilimlerindeki değişimleri al
        change_1h = abs(features.get("percent_change_1h", 0))
        change_24h = abs(features.get("percent_change_24h", 0))
        change_7d = abs(features.get("percent_change_7d", 0))
        
        # Ağırlıklı ortalama (yakın dönem daha önemli)
        # 1h: 50%, 24h: 30%, 7d: 20%
        volatility = (change_1h * 0.5) + (change_24h * 0.3) + (change_7d * 0.2)
        
        logger.debug(f"Volatility calculated: {volatility:.2f}% (1h:{change_1h:.2f}, 24h:{change_24h:.2f}, 7d:{change_7d:.2f})")
        
        return round(volatility, 2)
    
    except Exception as e:
        logger.error(f"Volatility calculation error: {e}")
        return 5.0  # Varsayılan orta düzey volatilite


def calculate_dynamic_threshold(volatility: float, timeframe: str = "24h") -> float:
    """
    Volatiliteye göre dinamik threshold hesapla
    
    Mantık:
    - Yüksek volatilite → Yüksek threshold (daha seçici)
    - Düşük volatilite → Düşük threshold (daha hassas)
    
    Timeframe Etkisi:
    - Kısa vadeli (15m, 1h): Daha düşük threshold
    - Orta vadeli (4h, 24h): Orta threshold
    - Uzun vadeli (7d, 30d): Daha yüksek threshold
    
    Args:
        volatility: Hesaplanan volatilite değeri
        timeframe: Analiz zaman dilimi
    
    Returns:
        float: Dinamik threshold değeri (0-100 arası)
    """
    
    # Timeframe bazlı çarpanlar
    timeframe_multipliers = {
        "15m": 0.7,   # Kısa vade: daha düşük threshold
        "1h": 0.8,
        "4h": 0.9,
        "12h": 1.0,
        "24h": 1.0,   # Standart
        "1d": 1.0,
        "7d": 1.2,    # Uzun vade: daha yüksek threshold
        "1w": 1.2,
        "30d": 1.3,
        "1m": 1.3
    }
    
    multiplier = timeframe_multipliers.get(timeframe, 1.0)
    
    # Volatiliteye göre temel threshold
    if volatility > 15:
        # Çok yüksek volatilite: Çok seçici ol
        base_threshold = 8.0
    elif volatility > 10:
        # Yüksek volatilite: Seçici ol
        base_threshold = 5.0
    elif volatility > 7:
        # Orta-yüksek volatilite
        base_threshold = 3.5
    elif volatility > 5:
        # Orta volatilite
        base_threshold = 2.5
    elif volatility > 3:
        # Orta-düşük volatilite
        base_threshold = 1.5
    elif volatility > 1:
        # Düşük volatilite
        base_threshold = 1.0
    else:
        # Çok düşük volatilite: Hassas ol
        base_threshold = 0.5
    
    # Timeframe çarpanını uygula
    dynamic_threshold = base_threshold * multiplier
    
    # Minimum 0.5, maksimum 15
    dynamic_threshold = max(0.5, min(15.0, dynamic_threshold))
    
    logger.info(f"Dynamic threshold calculated: {dynamic_threshold:.2f}% "
                f"(volatility: {volatility:.2f}%, timeframe: {timeframe}, multiplier: {multiplier})")
    
    return round(dynamic_threshold, 2)


def get_threshold(features: dict, threshold_mode: str, manual_threshold: float, timeframe: str = "24h") -> float:
    """
    Threshold alma fonksiyonu (manuel veya dinamik)
    
    Args:
        features: Coin özellikleri
        threshold_mode: "manual" veya "dynamic"
        manual_threshold: Manuel threshold değeri
        timeframe: Analiz zaman dilimi
    
    Returns:
        float: Kullanılacak threshold değeri
    """
    if threshold_mode == "dynamic":
        volatility = calculate_volatility(features)
        threshold = calculate_dynamic_threshold(volatility, timeframe)
        logger.info(f"Using DYNAMIC threshold: {threshold}% (volatility: {volatility}%)")
        return threshold
    else:
        logger.info(f"Using MANUAL threshold: {manual_threshold}%")
        return manual_threshold
