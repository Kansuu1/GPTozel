# backend/manual_price_override.py
"""
Manuel fiyat override sistemi
Kullanıcı belirli coinler için manuel fiyat belirleyebilir
"""
import logging
from typing import Optional, Dict
from db_mongodb import get_db

logger = logging.getLogger(__name__)


def set_manual_price(coin: str, price: float, source: str = "manual") -> bool:
    """
    Coin için manuel fiyat belirle
    
    Args:
        coin: Coin sembolü
        price: Manuel fiyat
        source: Kaynak açıklaması
    
    Returns:
        Başarılı mı?
    """
    try:
        db = get_db()
        
        override = {
            "coin": coin.upper(),
            "price": price,
            "source": source,
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Upsert (varsa güncelle, yoksa ekle)
        db.manual_price_overrides.update_one(
            {"coin": coin.upper()},
            {"$set": override},
            upsert=True
        )
        
        logger.info(f"✅ [{coin}] Manuel fiyat belirlendi: ${price} (Kaynak: {source})")
        return True
    
    except Exception as e:
        logger.error(f"❌ Manuel fiyat belirleme hatası [{coin}]: {e}")
        return False


def get_manual_price(coin: str) -> Optional[float]:
    """
    Coin için manuel fiyatı getir
    
    Args:
        coin: Coin sembolü
    
    Returns:
        Manuel fiyat veya None
    """
    try:
        db = get_db()
        
        override = db.manual_price_overrides.find_one({"coin": coin.upper()})
        
        if override:
            price = override["price"]
            logger.info(f"📌 [{coin}] Manuel fiyat kullanılıyor: ${price}")
            return price
        
        return None
    
    except Exception as e:
        logger.error(f"❌ Manuel fiyat okuma hatası [{coin}]: {e}")
        return None


def remove_manual_price(coin: str) -> bool:
    """
    Manuel fiyat override'ı kaldır
    
    Args:
        coin: Coin sembolü
    
    Returns:
        Başarılı mı?
    """
    try:
        db = get_db()
        
        result = db.manual_price_overrides.delete_one({"coin": coin.upper()})
        
        if result.deleted_count > 0:
            logger.info(f"✅ [{coin}] Manuel fiyat kaldırıldı")
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"❌ Manuel fiyat kaldırma hatası [{coin}]: {e}")
        return False


def get_all_manual_prices() -> Dict[str, float]:
    """
    Tüm manuel fiyat override'larını getir
    
    Returns:
        {coin: price} dictionary
    """
    try:
        db = get_db()
        
        overrides = list(db.manual_price_overrides.find())
        
        return {o["coin"]: o["price"] for o in overrides}
    
    except Exception as e:
        logger.error(f"❌ Manuel fiyatlar okuma hatası: {e}")
        return {}
