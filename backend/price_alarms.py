# backend/price_alarms.py
"""
Fiyat alarm sistemi
Sinyal üretildiğinde otomatik alarm oluşturur
Fiyat hedef seviyeye ulaşınca Telegram bildirimi gönderir
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from db_mongodb import get_db

logger = logging.getLogger(__name__)


def create_price_alarm(
    coin: str,
    target_price: float,
    alarm_type: str,  # "target" (giriş fiyatı)
    signal_id: Optional[str] = None,
    signal_type: Optional[str] = None
) -> str:
    """
    Yeni fiyat alarmı oluştur
    
    Args:
        coin: Coin sembolü (örn: BTC)
        target_price: Hedef fiyat
        alarm_type: Alarm tipi ("target")
        signal_id: İlişkili sinyal ID'si
        signal_type: Sinyal tipi (LONG/SHORT)
    
    Returns:
        Alarm ID
    """
    try:
        db = get_db()
        
        alarm = {
            "coin": coin,
            "target_price": target_price,
            "alarm_type": alarm_type,
            "signal_id": signal_id,
            "signal_type": signal_type,
            "is_active": True,
            "triggered": False,
            "created_at": datetime.now(timezone.utc),
            "triggered_at": None
        }
        
        result = db.price_alarms.insert_one(alarm)
        alarm_id = str(result.inserted_id)
        
        logger.info(f"✅ [{coin}] Fiyat alarmı oluşturuldu: {target_price}$ (ID: {alarm_id})")
        return alarm_id
    
    except Exception as e:
        logger.error(f"❌ Alarm oluşturma hatası [{coin}]: {e}")
        return None


def check_price_alarms(coin: str, current_price: float) -> List[Dict]:
    """
    Coin için aktif alarmları kontrol et
    Tetiklenen alarmları döndür
    
    Args:
        coin: Coin sembolü
        current_price: Güncel fiyat
    
    Returns:
        Tetiklenen alarmlar listesi
    """
    try:
        db = get_db()
        
        # Aktif alarmları al
        alarms = list(db.price_alarms.find({
            "coin": coin,
            "is_active": True,
            "triggered": False
        }).limit(100))
        
        triggered_alarms = []
        
        for alarm in alarms:
            target_price = alarm["target_price"]
            alarm_type = alarm["alarm_type"]
            
            # Alarm kontrolü
            should_trigger = False
            
            if alarm_type == "target":
                # Hedef fiyata ulaşıldı mı? (%0.5 tolerans)
                tolerance = target_price * 0.005
                if abs(current_price - target_price) <= tolerance:
                    should_trigger = True
            
            if should_trigger:
                # Alarmı tetikle
                db.price_alarms.update_one(
                    {"_id": alarm["_id"]},
                    {
                        "$set": {
                            "triggered": True,
                            "triggered_at": datetime.now(timezone.utc),
                            "triggered_price": current_price
                        }
                    }
                )
                
                alarm["triggered_price"] = current_price
                triggered_alarms.append(alarm)
                
                logger.info(f"🔔 [{coin}] Alarm tetiklendi! Hedef: {target_price}$, Güncel: {current_price}$")
        
        return triggered_alarms
    
    except Exception as e:
        logger.error(f"❌ Alarm kontrolü hatası [{coin}]: {e}")
        return []


async def get_active_alarms(coin: Optional[str] = None) -> List[Dict]:
    """
    Aktif alarmları getir
    
    Args:
        coin: Coin sembolü (None ise tüm coinler)
    
    Returns:
        Aktif alarmlar listesi
    """
    try:
        db = await get_db()
        
        query = {"is_active": True, "triggered": False}
        if coin:
            query["coin"] = coin
        
        alarms = await db.price_alarms.find(query).sort("created_at", -1).to_list(length=100)
        
        # ObjectId'yi string'e çevir
        for alarm in alarms:
            alarm["_id"] = str(alarm["_id"])
            if alarm.get("signal_id"):
                alarm["signal_id"] = str(alarm["signal_id"])
        
        return alarms
    
    except Exception as e:
        logger.error(f"❌ Alarm listesi hatası: {e}")
        return []


async def delete_alarm(alarm_id: str) -> bool:
    """
    Alarmı sil veya deaktive et
    
    Args:
        alarm_id: Alarm ID
    
    Returns:
        Başarılı mı?
    """
    try:
        db = await get_db()
        from bson import ObjectId
        
        result = await db.price_alarms.update_one(
            {"_id": ObjectId(alarm_id)},
            {"$set": {"is_active": False}}
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Alarm silindi: {alarm_id}")
            return True
        return False
    
    except Exception as e:
        logger.error(f"❌ Alarm silme hatası: {e}")
        return False


async def get_alarm_statistics() -> Dict:
    """
    Alarm istatistikleri
    
    Returns:
        {
            "total_active": int,
            "total_triggered": int,
            "by_coin": {...}
        }
    """
    try:
        db = await get_db()
        
        # Aktif alarmlar
        active_count = await db.price_alarms.count_documents({
            "is_active": True,
            "triggered": False
        })
        
        # Tetiklenen alarmlar
        triggered_count = await db.price_alarms.count_documents({
            "triggered": True
        })
        
        # Coin bazında
        pipeline = [
            {"$match": {"is_active": True, "triggered": False}},
            {"$group": {"_id": "$coin", "count": {"$sum": 1}}}
        ]
        by_coin_cursor = db.price_alarms.aggregate(pipeline)
        by_coin = {item["_id"]: item["count"] async for item in by_coin_cursor}
        
        return {
            "total_active": active_count,
            "total_triggered": triggered_count,
            "by_coin": by_coin
        }
    
    except Exception as e:
        logger.error(f"❌ Alarm istatistikleri hatası: {e}")
        return {"total_active": 0, "total_triggered": 0, "by_coin": {}}
