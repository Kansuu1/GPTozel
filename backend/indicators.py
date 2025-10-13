# backend/indicators.py
"""
Teknik göstergeler: RSI, MACD, EMA ve Adaptive Timeframe
"""
import numpy as np
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def select_adaptive_timeframe(volatility: float) -> str:
    """
    Volatiliteye göre optimal timeframe seç
    
    Args:
        volatility: Volatilite yüzdesi (0-100)
    
    Returns:
        Timeframe string ("15m", "30m", "1h", "4h", "6h", "12h", "24h", "7d", "30d")
    """
    # Volatilite seviyelerine göre timeframe seçimi
    if volatility >= 12.0:
        # Çok yüksek volatilite - Çok kısa vadeli
        timeframe = "15m"
        logger.info(f"📊 Adaptive Timeframe: 15 dakika seçildi (Volatilite: {volatility:.1f}% - ÇOK YÜKSEK)")
    elif volatility >= 8.0:
        # Yüksek volatilite - Kısa vadeli
        timeframe = "30m"
        logger.info(f"📊 Adaptive Timeframe: 30 dakika seçildi (Volatilite: {volatility:.1f}% - YÜKSEK)")
    elif volatility >= 5.0:
        # Orta-yüksek volatilite
        timeframe = "1h"
        logger.info(f"📊 Adaptive Timeframe: 1 saat seçildi (Volatilite: {volatility:.1f}% - ORTA-YÜKSEK)")
    elif volatility >= 3.0:
        # Orta volatilite
        timeframe = "4h"
        logger.info(f"📊 Adaptive Timeframe: 4 saat seçildi (Volatilite: {volatility:.1f}% - ORTA)")
    elif volatility >= 2.0:
        # Orta-düşük volatilite
        timeframe = "6h"
        logger.info(f"📊 Adaptive Timeframe: 6 saat seçildi (Volatilite: {volatility:.1f}% - ORTA-DÜŞÜK)")
    elif volatility >= 1.5:
        # Düşük volatilite - Yarım gün
        timeframe = "12h"
        logger.info(f"📊 Adaptive Timeframe: 12 saat seçildi (Volatilite: {volatility:.1f}% - DÜŞÜK)")
    elif volatility >= 1.0:
        # Düşük volatilite - Günlük
        timeframe = "24h"
        logger.info(f"📊 Adaptive Timeframe: 24 saat seçildi (Volatilite: {volatility:.1f}% - DÜŞÜK)")
    elif volatility >= 0.5:
        # Çok düşük volatilite - Haftalık
        timeframe = "7d"
        logger.info(f"📊 Adaptive Timeframe: 7 gün seçildi (Volatilite: {volatility:.1f}% - ÇOK DÜŞÜK)")
    else:
        # Minimal volatilite - Aylık
        timeframe = "30d"
        logger.info(f"📊 Adaptive Timeframe: 30 gün seçildi (Volatilite: {volatility:.1f}% - MİNİMAL)")
    
    return timeframe


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


def get_ema_cross_signal(ema50: float, ema200: float) -> str:
    """
    EMA50 ve EMA200 kesişimine göre Golden/Death Cross tespiti
    
    Args:
        ema50: 50 periyotluk EMA
        ema200: 200 periyotluk EMA
    
    Returns:
        "GOLDEN_CROSS" (EMA50 > EMA200 - Güçlü yükseliş),
        "DEATH_CROSS" (EMA50 < EMA200 - Güçlü düşüş),
        "NEUTRAL"
    """
    if ema50 is None or ema200 is None:
        return "NEUTRAL"
    
    diff_percent = ((ema50 - ema200) / ema200) * 100
    
    # EMA50 > EMA200 = Golden Cross (Yükseliş)
    if diff_percent > 0.5:  # %0.5'ten fazla yukarıda
        return "GOLDEN_CROSS"
    # EMA50 < EMA200 = Death Cross (Düşüş)
    elif diff_percent < -0.5:  # %0.5'ten fazla aşağıda
        return "DEATH_CROSS"
    
    return "NEUTRAL"


def calculate_volatility(prices: List[float]) -> float:
    """
    Fiyat volatilitesi hesapla (standart sapma / ortalama)
    
    Args:
        prices: Fiyat listesi
    
    Returns:
        Volatilite yüzdesi (0-100)
    """
    if len(prices) < 2:
        return 0.0
    
    try:
        prices_array = np.array(prices)
        mean = np.mean(prices_array)
        std = np.std(prices_array)
        
        # Coefficient of Variation (CV) - yüzde cinsinden
        volatility = (std / mean) * 100 if mean > 0 else 0
        
        return round(float(volatility), 2)
    
    except Exception as e:
        logger.error(f"Volatilite hesaplama hatası: {e}")
        return 0.0


def calculate_signal_strength(indicators: dict) -> dict:
    """
    RSI, MACD ve EMA'dan combined signal strength hesapla
    
    Args:
        indicators: Tüm göstergeler dictionary
    
    Returns:
        {
            "score": float (0-100),
            "level": str (VERY_WEAK, WEAK, MODERATE, STRONG, VERY_STRONG),
            "direction": str (BULLISH, BEARISH, NEUTRAL)
        }
    """
    score = 0
    bullish_signals = 0
    bearish_signals = 0
    total_signals = 0
    
    # RSI sinyali (30 puan)
    if indicators.get("rsi_signal"):
        total_signals += 1
        if indicators["rsi_signal"] == "OVERSOLD":
            bullish_signals += 1
            score += 30
        elif indicators["rsi_signal"] == "OVERBOUGHT":
            bearish_signals += 1
            score += 30
    
    # MACD sinyali (35 puan)
    if indicators.get("macd_signal"):
        total_signals += 1
        if indicators["macd_signal"] == "BULLISH":
            bullish_signals += 1
            score += 35
        elif indicators["macd_signal"] == "BEARISH":
            bearish_signals += 1
            score += 35
    
    # EMA kısa vadeli sinyal (20 puan)
    if indicators.get("ema_signal"):
        total_signals += 1
        if indicators["ema_signal"] == "BULLISH":
            bullish_signals += 1
            score += 20
        elif indicators["ema_signal"] == "BEARISH":
            bearish_signals += 1
            score += 20
    
    # EMA uzun vadeli sinyal (Golden/Death Cross) (15 puan)
    if indicators.get("ema_cross"):
        total_signals += 1
        if indicators["ema_cross"] == "GOLDEN_CROSS":
            bullish_signals += 1
            score += 15
        elif indicators["ema_cross"] == "DEATH_CROSS":
            bearish_signals += 1
            score += 15
    
    # Yön belirle
    if bullish_signals > bearish_signals:
        direction = "BULLISH"
    elif bearish_signals > bullish_signals:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"
    
    # Seviye belirle
    if score >= 80:
        level = "VERY_STRONG"
    elif score >= 60:
        level = "STRONG"
    elif score >= 40:
        level = "MODERATE"
    elif score >= 20:
        level = "WEAK"
    else:
        level = "VERY_WEAK"
    
    return {
        "score": round(score, 1),
        "level": level,
        "direction": direction,
        "bullish_count": bullish_signals,
        "bearish_count": bearish_signals,
        "total_count": total_signals
    }


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
    
    # EMA hesapla (kısa vadeli)
    ema9 = calculate_ema(prices, period=9)
    ema21 = calculate_ema(prices, period=21)
    
    # EMA hesapla (uzun vadeli)
    ema50 = calculate_ema(prices, period=50)
    ema200 = calculate_ema(prices, period=200)
    
    current_price = prices[-1] if prices else 0
    
    # Kısa vadeli EMA
    if ema9 is not None and ema21 is not None:
        result["ema9"] = ema9
        result["ema21"] = ema21
        result["ema_signal"] = get_ema_signal(ema9, ema21, current_price)
    
    # Uzun vadeli EMA
    if ema50 is not None:
        result["ema50"] = ema50
    if ema200 is not None:
        result["ema200"] = ema200
    
    # Golden Cross / Death Cross tespiti
    if ema50 is not None and ema200 is not None:
        result["ema_cross"] = get_ema_cross_signal(ema50, ema200)
    
    # Volatilite hesapla (son 20 fiyat için)
    if len(prices) >= 20:
        volatility = calculate_volatility(prices[-20:])
        result["volatility"] = volatility
    
    # Combined Signal Strength (RSI + MACD + EMA)
    result["signal_strength"] = calculate_signal_strength(result)
    
    return result
