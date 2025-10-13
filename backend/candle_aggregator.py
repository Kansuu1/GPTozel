# backend/candle_aggregator.py
"""
Candle Interval Aggregation
Ham fiyat verilerini candle interval'e göre aggregate eder
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


def parse_interval_to_minutes(interval: str) -> int:
    """
    Interval string'ini dakikaya çevir
    
    Args:
        interval: '15m', '1h', '4h', '24h', '7d', '30d' vb.
    
    Returns:
        Dakika cinsinden süre
    """
    if not interval:
        return 0
    
    try:
        if interval.endswith('m'):
            return int(interval[:-1])
        elif interval.endswith('h'):
            return int(interval[:-1]) * 60
        elif interval.endswith('d'):
            return int(interval[:-1]) * 24 * 60
        else:
            logger.warning(f"Bilinmeyen interval formatı: {interval}")
            return 0
    except Exception as e:
        logger.error(f"Interval parse hatası: {interval} - {e}")
        return 0


def aggregate_prices_to_candles(
    price_data: List[Dict], 
    candle_interval: str
) -> List[float]:
    """
    Ham fiyat verilerini candle interval'e göre aggregate et
    
    Args:
        price_data: [{"price": float, "timestamp": datetime}, ...]
        candle_interval: '15m', '1h', '4h', vb.
    
    Returns:
        Candle close price listesi (en yeni sonda)
    """
    if not price_data or not candle_interval:
        return [p["price"] for p in price_data]
    
    # Interval'i dakikaya çevir
    interval_minutes = parse_interval_to_minutes(candle_interval)
    if interval_minutes == 0:
        # Parse başarısız, raw price'ları döndür
        return [p["price"] for p in price_data]
    
    # Timestamp'e göre sırala (eskiden yeniye)
    sorted_data = sorted(price_data, key=lambda x: x["timestamp"])
    
    if not sorted_data:
        return []
    
    # Candle'ları oluştur
    candles = []
    current_candle_start = None
    current_candle_data = []
    
    for data_point in sorted_data:
        timestamp = data_point["timestamp"]
        price = data_point["price"]
        
        # İlk candle başlat
        if current_candle_start is None:
            current_candle_start = timestamp
            current_candle_data = [price]
            continue
        
        # Yeni candle'a geçiş zamanı mı?
        time_diff = (timestamp - current_candle_start).total_seconds() / 60  # dakika
        
        if time_diff >= interval_minutes:
            # Mevcut candle'ı kapat (close price = son fiyat)
            if current_candle_data:
                candles.append(current_candle_data[-1])  # Close price
            
            # Yeni candle başlat
            current_candle_start = timestamp
            current_candle_data = [price]
        else:
            # Aynı candle'a ekle
            current_candle_data.append(price)
    
    # Son candle'ı ekle
    if current_candle_data:
        candles.append(current_candle_data[-1])
    
    logger.info(f"📊 Candle Aggregation: {len(price_data)} ham veri → {len(candles)} candle ({candle_interval})")
    
    return candles


def check_sufficient_data_for_analysis(
    candle_count: int,
    require_macd: bool = True
) -> Tuple[bool, str]:
    """
    Analiz için yeterli candle var mı kontrol et
    
    Args:
        candle_count: Mevcut candle sayısı
        require_macd: MACD gerekli mi?
    
    Returns:
        (yeterli_mi, mesaj)
    """
    # RSI için minimum 15 candle
    if candle_count < 15:
        return False, f"RSI için {15 - candle_count} candle daha gerekli"
    
    # MACD için minimum 26 candle
    if require_macd and candle_count < 26:
        return False, f"MACD için {26 - candle_count} candle daha gerekli"
    
    return True, "Yeterli veri mevcut"


def get_recommended_fetch_interval(candle_interval: str) -> int:
    """
    Candle interval'e göre önerilen fetch interval (dakika)
    
    Args:
        candle_interval: '15m', '1h', '4h', vb.
    
    Returns:
        Önerilen fetch interval (dakika)
    """
    interval_minutes = parse_interval_to_minutes(candle_interval)
    
    if interval_minutes == 0:
        return 5  # Default
    
    # Candle interval'in 1/5'i veya minimum 1 dakika
    recommended = max(1, interval_minutes // 5)
    
    # Maksimum 60 dakika
    recommended = min(60, recommended)
    
    return recommended
