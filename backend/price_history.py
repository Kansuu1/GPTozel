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
        
        result = db.price_history.insert_one(price_point)
        # İlk birkaç kayıt için log
        count = db.price_history.count_documents({"coin": coin})
        if count <= 5 or count % 10 == 0:
            logger.info(f"💾 [{coin}] Fiyat kaydedildi: ${price:.4f} (Toplam: {count} kayıt)")
        
        # Eski verileri temizle (90 günden eski)
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        deleted = db.price_history.delete_many({
            "coin": coin,
            "timestamp": {"$lt": cutoff}
        })
        if deleted.deleted_count > 0:
            logger.info(f"🗑️ [{coin}] {deleted.deleted_count} eski kayıt silindi")
        
    except Exception as e:
        logger.error(f"❌ Fiyat kaydetme hatası [{coin}]: {e}", exc_info=True)


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


def get_recent_prices(coin: str, hours: int = 24, count: int = None) -> List[float]:
    """
    Coin için son fiyatları getir (sadece fiyatlar)
    
    Args:
        coin: Coin sembolü
        hours: Kaç saatlik geçmiş (default: 24)
        count: Maksimum kayıt sayısı (optional)
    
    Returns:
        Fiyat listesi (en eskiden yeniye)
    """
    try:
        db = get_db()
        
        # Zaman aralığı
        if count is None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            cursor = db.price_history.find({
                "coin": coin,
                "timestamp": {"$gte": cutoff}
            }).sort("timestamp", 1)  # Eskiden yeniye
        else:
            cursor = db.price_history.find({
                "coin": coin
            }).sort("timestamp", -1).limit(count)  # En yeni count kadar
            
            # Liste halinde al ve ters çevir (eskiden yeniye)
            records = list(cursor)
            records.reverse()
            return [r["price"] for r in records if "price" in r]
        
        prices = [r["price"] for r in cursor if "price" in r]
        return prices
    
    except Exception as e:
        logger.error(f"Fiyat geçmişi okuma hatası [{coin}]: {e}")
        return []


def get_recent_prices_with_timestamps(coin: str, hours: int = 24) -> List[dict]:
    """
    Coin için son fiyatları timestamp ile getir
    
    Args:
        coin: Coin sembolü
        hours: Kaç saatlik geçmiş (default: 24)
    
    Returns:
        [{"price": float, "timestamp": datetime}, ...] (en eskiden yeniye)
    """
    try:
        db = get_db()
        
        # Zaman aralığı
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cursor = db.price_history.find({
            "coin": coin,
            "timestamp": {"$gte": cutoff}
        }).sort("timestamp", 1)  # Eskiden yeniye
        
        price_data = []
        for record in cursor:
            if "price" in record and "timestamp" in record:
                price_data.append({
                    "price": record["price"],
                    "timestamp": record["timestamp"]
                })
        
        return price_data
    
    except Exception as e:
        logger.error(f"Fiyat geçmişi (timestamp) okuma hatası [{coin}]: {e}")
        return []


def get_price_statistics(coin: str, hours: int = 24) -> dict:
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
        prices = get_price_history(coin, hours=hours)
        
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


def cleanup_old_prices(days: int = 90):
    """
    Eski fiyat verilerini temizle
    
    Args:
        days: Kaç günden eski veriler silinsin
    """
    try:
        db = get_db()
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        result = db.price_history.delete_many({
            "timestamp": {"$lt": cutoff}
        })
        
        if result.deleted_count > 0:
            logger.info(f"🗑️ {result.deleted_count} eski fiyat verisi silindi")
    
    except Exception as e:
        logger.error(f"❌ Fiyat temizleme hatası: {e}")
