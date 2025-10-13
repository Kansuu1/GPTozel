# backend/indicators.py
"""
Teknik göstergeler: RSI, MACD
"""
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
    """
    RSI (Relative Strength Index) hesapla
    
    Args:
        prices: Fiyat listesi (en yeni fiyat sonda)
        period: RSI periyodu (varsayılan 14)
    
    Returns:
        RSI değeri (0-100 arası) veya None
    """
    if len(prices) < period + 1:
        return None
    
    try:
        # Fiyat değişimlerini hesapla
        deltas = np.diff(prices)
        
        # Kazanç ve kayıpları ayır
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # İlk ortalama
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        # Sonraki değerler için smoothed averages
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        # RSI hesapla
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    except Exception as e:
        logger.error(f"RSI hesaplama hatası: {e}")
        return None


def calculate_macd(prices: List[float], 
                   fast_period: int = 12, 
                   slow_period: int = 26, 
                   signal_period: int = 9) -> Optional[Tuple[float, float, float]]:
    """
    MACD (Moving Average Convergence Divergence) hesapla
    
    Args:
        prices: Fiyat listesi (en yeni fiyat sonda)
        fast_period: Hızlı EMA periyodu (varsayılan 12)
        slow_period: Yavaş EMA periyodu (varsayılan 26)
        signal_period: Sinyal çizgisi periyodu (varsayılan 9)
    
    Returns:
        (MACD, Signal, Histogram) tuple veya None
    """
    # Minimum slow_period kadar veri gerekli (signal için daha az tolere edebiliriz)
    if len(prices) < slow_period:
        return None
    
    try:
        prices_array = np.array(prices)
        
        # EMA hesaplama fonksiyonu
        def calculate_ema(data, period):
            multiplier = 2 / (period + 1)
            ema = [data[0]]  # İlk değer
            for price in data[1:]:
                ema.append((price - ema[-1]) * multiplier + ema[-1])
            return np.array(ema)
        
        # Hızlı ve yavaş EMA'ları hesapla
        fast_ema = calculate_ema(prices_array, fast_period)
        slow_ema = calculate_ema(prices_array, slow_period)
        
        # MACD line = Fast EMA - Slow EMA
        macd_line = fast_ema - slow_ema
        
        # Signal line = MACD'nin EMA'sı (yeterli veri varsa)
        if len(macd_line) >= signal_period:
            signal_line = calculate_ema(macd_line, signal_period)
            # Histogram = MACD - Signal
            histogram = macd_line - signal_line
        else:
            # Yeterli veri yoksa sadece MACD line kullan
            signal_line = np.array([macd_line[-1]])
            histogram = np.array([0.0])
        
        # En son değerleri döndür
        return (
            round(float(macd_line[-1]), 4),
            round(float(signal_line[-1]), 4),
            round(float(histogram[-1]), 4)
        )
    
    except Exception as e:
        logger.error(f"MACD hesaplama hatası: {e}")
        return None


def get_rsi_signal(rsi: float) -> str:
    """
    RSI değerine göre sinyal üret
    
    Returns:
        "OVERSOLD" (30 altı), "OVERBOUGHT" (70 üstü), "NEUTRAL"
    """
    if rsi < 30:
        return "OVERSOLD"  # Aşırı satım
    elif rsi > 70:
        return "OVERBOUGHT"  # Aşırı alım
    else:
        return "NEUTRAL"


def get_macd_signal(macd: float, signal: float, histogram: float) -> str:
    """
    MACD değerlerine göre sinyal üret
    
    Returns:
        "BULLISH" (MACD > Signal), "BEARISH" (MACD < Signal)
    """
    if macd > signal and histogram > 0:
        return "BULLISH"  # Yükseliş trendi
    elif macd < signal and histogram < 0:
        return "BEARISH"  # Düşüş trendi
    else:
        return "NEUTRAL"


def calculate_ema(prices: List[float], period: int) -> Optional[float]:
    """
    EMA (Exponential Moving Average) hesapla
    
    Args:
        prices: Fiyat listesi (en yeni fiyat sonda)
        period: EMA periyodu (örn: 9, 21)
    
    Returns:
        EMA değeri veya None
    """
    if len(prices) < period:
        return None
    
    try:
        prices_array = np.array(prices)
        multiplier = 2 / (period + 1)
        
        # İlk EMA = İlk N fiyatın ortalaması
        ema = np.mean(prices_array[:period])
        
        # Sonraki değerleri hesapla
        for price in prices_array[period:]:
            ema = (price - ema) * multiplier + ema
        
        return round(float(ema), 4)
    
    except Exception as e:
        logger.error(f"EMA hesaplama hatası: {e}")
        return None


def get_ema_signal(ema9: float, ema21: float, current_price: float) -> str:
    """
    EMA9 ve EMA21 kesişimine göre sinyal üret
    
    Args:
        ema9: 9 periyotluk EMA
        ema21: 21 periyotluk EMA
        current_price: Güncel fiyat
    
    Returns:
        "BULLISH" (EMA9 > EMA21 ve fiyat EMA9 üstünde),
        "BEARISH" (EMA9 < EMA21 ve fiyat EMA9 altında),
        "NEUTRAL"
    """
    if ema9 is None or ema21 is None:
        return "NEUTRAL"
    
    # EMA9 > EMA21 = Yükseliş trendi
    if ema9 > ema21:
        # Fiyat da EMA9'un üstündeyse güçlü bullish
        if current_price > ema9:
            return "BULLISH"
        else:
            return "NEUTRAL"
    
    # EMA9 < EMA21 = Düşüş trendi
    elif ema9 < ema21:
        # Fiyat da EMA9'un altındaysa güçlü bearish
        if current_price < ema9:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    return "NEUTRAL"


def calculate_indicators(prices: List[float]) -> dict:
    """
    Tüm göstergeleri hesapla ve döndür
    
    Args:
        prices: Fiyat listesi (en yeni fiyat sonda)
    
    Returns:
        {
            "rsi": float,
            "rsi_signal": str,
            "macd": float,
            "macd_signal_line": float,
            "macd_histogram": float,
            "macd_signal": str,
            "ema9": float,
            "ema21": float,
            "ema_signal": str
        }
    """
    result = {
        "rsi": None,
        "rsi_signal": None,
        "macd": None,
        "macd_signal_line": None,
        "macd_histogram": None,
        "macd_signal": None,
        "ema9": None,
        "ema21": None,
        "ema_signal": None
    }
    
    # RSI hesapla
    rsi = calculate_rsi(prices, period=14)
    if rsi is not None:
        result["rsi"] = rsi
        result["rsi_signal"] = get_rsi_signal(rsi)
    
    # MACD hesapla
    macd_result = calculate_macd(prices, fast_period=12, slow_period=26, signal_period=9)
    if macd_result is not None:
        macd, signal, histogram = macd_result
        result["macd"] = macd
        result["macd_signal_line"] = signal
        result["macd_histogram"] = histogram
        result["macd_signal"] = get_macd_signal(macd, signal, histogram)
    
    # EMA hesapla
    ema9 = calculate_ema(prices, period=9)
    ema21 = calculate_ema(prices, period=21)
    
    if ema9 is not None and ema21 is not None:
        current_price = prices[-1] if prices else 0
        result["ema9"] = ema9
        result["ema21"] = ema21
        result["ema_signal"] = get_ema_signal(ema9, ema21, current_price)
    
    return result
