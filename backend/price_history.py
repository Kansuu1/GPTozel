# backend/price_history.py
"""
Fiyat geçmişi yönetimi
RSI ve MACD hesaplamaları için gerekli fiyat verilerini saklar
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from db_mongodb import get_db

logger = logging.getLogger(__name__)


def save_price_point(coin: str, price: float, volume_24h: float = 0):
    """
    Coin için fiyat noktası kaydet
    
    Args:
        coin: Coin sembolü
        price: Fiyat
        volume_24h: 24 saatlik hacim
    """
    try:
        db = get_db()
        
        price_point = {
            "coin": coin,
            "price": price,
            "volume_24h": volume_24h,
            "timestamp": datetime.now(timezone.utc)
        }
        
        db.price_history.insert_one(price_point)
        
        # Eski verileri temizle (90 günden eski)
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        db.price_history.delete_many({
            "coin": coin,
            "timestamp": {"$lt": cutoff}
        })
        
    except Exception as e:
        logger.error(f"❌ Fiyat kaydetme hatası [{coin}]: {e}")


def get_price_history(coin: str, hours: int = 24, limit: int = 500) -> List[float]:
    """
    Coin için fiyat geçmişini getir
    
    Args:
        coin: Coin sembolü
        hours: Kaç saatlik geçmiş (varsayılan 24)
        limit: Maksimum kayıt sayısı
    
    Returns:
        Fiyat listesi (eski → yeni)
    """
    try:
        db = get_db()
        
        # Zaman aralığını belirle
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Fiyat geçmişini getir
        cursor = db.price_history.find({
            "coin": coin,
            "timestamp": {"$gte": cutoff}
        }).sort("timestamp", 1).limit(limit)
        
        prices = [doc["price"] for doc in cursor]
        
        return prices
    
    except Exception as e:
        logger.error(f"❌ Fiyat geçmişi hatası [{coin}]: {e}")
        return []


async def get_recent_prices(coin: str, count: int = 50) -> List[float]:
    """
    Son N fiyat noktasını getir
    
    Args:
        coin: Coin sembolü
        count: Kaç adet
    
    Returns:
        Fiyat listesi (eski → yeni)
    """
    try:
        db = await get_db()
        
        cursor = db.price_history.find({
            "coin": coin
        }).sort("timestamp", -1).limit(count)
        
        prices = [doc["price"] async for doc in cursor]
        prices.reverse()  # Eski → yeni sırala
        
        return prices
    
    except Exception as e:
        logger.error(f"❌ Son fiyatlar hatası [{coin}]: {e}")
        return []


async def get_price_statistics(coin: str, hours: int = 24) -> dict:
    """
    Fiyat istatistikleri
    
    Args:
        coin: Coin sembolü
        hours: Kaç saatlik periyot
    
    Returns:
        {
            "min": float,
            "max": float,
            "avg": float,
            "change_percent": float
        }
    """
    try:
        prices = await get_price_history(coin, hours=hours)
        
        if not prices or len(prices) < 2:
            return None
        
        min_price = min(prices)
        max_price = max(prices)
        avg_price = sum(prices) / len(prices)
        
        # Değişim yüzdesi
        first_price = prices[0]
        last_price = prices[-1]
        change_percent = ((last_price - first_price) / first_price) * 100
        
        return {
            "min": round(min_price, 8),
            "max": round(max_price, 8),
            "avg": round(avg_price, 8),
            "change_percent": round(change_percent, 2),
            "data_points": len(prices)
        }
    
    except Exception as e:
        logger.error(f"❌ Fiyat istatistikleri hatası [{coin}]: {e}")
        return None


async def cleanup_old_prices(days: int = 90):
    """
    Eski fiyat verilerini temizle
    
    Args:
        days: Kaç günden eski veriler silinsin
    """
    try:
        db = await get_db()
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        result = await db.price_history.delete_many({
            "timestamp": {"$lt": cutoff}
        })
        
        if result.deleted_count > 0:
            logger.info(f"🗑️ {result.deleted_count} eski fiyat verisi silindi")
    
    except Exception as e:
        logger.error(f"❌ Fiyat temizleme hatası: {e}")
