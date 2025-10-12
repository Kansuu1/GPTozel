# backend/db_mongodb.py - MongoDB Version
import os
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# MongoDB bağlantısı
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "crypto_bot")

# Global MongoDB client ve database
_client = None
_db = None

def get_db():
    """MongoDB database instance'ını döndür"""
    global _client, _db
    if _db is None:
        try:
            _client = MongoClient(MONGO_URL)
            _db = _client[DB_NAME]
            logger.info(f"✅ MongoDB bağlantısı başarılı: {DB_NAME}")
        except Exception as e:
            logger.error(f"❌ MongoDB bağlantı hatası: {e}")
            raise
    return _db

def init_db():
    """MongoDB collections ve indexler oluştur"""
    try:
        db = get_db()
        
        # signal_history collection için indexler
        db.signal_history.create_index([("coin", 1)])
        db.signal_history.create_index([("created_at", DESCENDING)])
        db.signal_history.create_index([("coin", 1), ("timeframe", 1)])
        
        # performance_agg collection için indexler
        db.performance_agg.create_index([("coin", 1), ("timeframe", 1)], unique=True)
        
        logger.info("✅ MongoDB collections ve indexler hazır")
    except Exception as e:
        logger.error(f"❌ MongoDB init hatası: {e}")
        raise

# Helper fonksiyonlar - MongoDB
def insert_signal_record(rec: dict):
    """Yeni sinyal kaydı ekle"""
    try:
        db = get_db()
        
        # created_at yoksa ekle
        if "created_at" not in rec:
            rec["created_at"] = datetime.now(timezone.utc)
        
        result = db.signal_history.insert_one(rec)
        return str(result.inserted_id)
    except Exception as e:
        logger.error(f"❌ Signal insert hatası: {e}")
        raise

def fetch_recent_signals(limit=100):
    """En son sinyalleri getir"""
    try:
        db = get_db()
        cursor = db.signal_history.find().sort("created_at", DESCENDING).limit(limit)
        
        # MongoDB dökümanlarını dict listesine çevir
        signals = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])  # _id'yi id'ye çevir
            signals.append(doc)
        
        return signals
    except Exception as e:
        logger.error(f"❌ Fetch signals hatası: {e}")
        return []

def get_signal_by_id(signal_id: str):
    """ID'ye göre sinyal getir"""
    try:
        db = get_db()
        from bson.objectid import ObjectId
        
        if not ObjectId.is_valid(signal_id):
            return None
        
        doc = db.signal_history.find_one({"_id": ObjectId(signal_id)})
        if doc:
            doc["id"] = str(doc["_id"])
        return doc
    except Exception as e:
        logger.error(f"❌ Get signal by ID hatası: {e}")
        return None

def update_signal_success(signal_id: str, success: bool, reward: float = None):
    """Sinyal başarı durumunu güncelle"""
    try:
        db = get_db()
        from bson.objectid import ObjectId
        
        if not ObjectId.is_valid(signal_id):
            return False
        
        update_data = {"success": success}
        if reward is not None:
            update_data["reward"] = reward
        
        result = db.signal_history.update_one(
            {"_id": ObjectId(signal_id)},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"❌ Update signal hatası: {e}")
        return False

def delete_signal(signal_id: str):
    """Sinyal sil"""
    try:
        db = get_db()
        from bson.objectid import ObjectId
        
        if not ObjectId.is_valid(signal_id):
            return False
        
        result = db.signal_history.delete_one({"_id": ObjectId(signal_id)})
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"❌ Delete signal hatası: {e}")
        return False

def clear_all_signals():
    """Tüm sinyalleri temizle"""
    try:
        db = get_db()
        result = db.signal_history.delete_many({})
        return result.deleted_count
    except Exception as e:
        logger.error(f"❌ Clear all signals hatası: {e}")
        return 0

def clear_failed_signals():
    """Başarısız sinyalleri temizle"""
    try:
        db = get_db()
        result = db.signal_history.delete_many({"success": False})
        return result.deleted_count
    except Exception as e:
        logger.error(f"❌ Clear failed signals hatası: {e}")
        return 0

def get_dashboard_stats():
    """Dashboard istatistikleri"""
    try:
        db = get_db()
        
        # Toplam sinyal
        total_signals = db.signal_history.count_documents({})
        
        # Başarılı, başarısız, bekleyen
        successful = db.signal_history.count_documents({"success": True})
        failed = db.signal_history.count_documents({"success": False})
        pending = db.signal_history.count_documents({"success": None})
        
        # Başarı oranı
        success_rate = (successful / total_signals * 100) if total_signals > 0 else 0
        
        # Maksimum kazanç/kayıp
        max_gain_doc = db.signal_history.find_one(
            {"reward": {"$ne": None}},
            sort=[("reward", DESCENDING)]
        )
        max_loss_doc = db.signal_history.find_one(
            {"reward": {"$ne": None}},
            sort=[("reward", 1)]
        )
        
        max_gain = max_gain_doc.get("reward", 0) if max_gain_doc else 0
        max_loss = max_loss_doc.get("reward", 0) if max_loss_doc else 0
        
        # Ortalama reward
        pipeline = [
            {"$match": {"reward": {"$ne": None}}},
            {"$group": {"_id": None, "avg_reward": {"$avg": "$reward"}}}
        ]
        avg_result = list(db.signal_history.aggregate(pipeline))
        avg_reward = avg_result[0]["avg_reward"] if avg_result else 0
        
        # Coin başına istatistikler
        coin_pipeline = [
            {"$group": {
                "_id": "$coin",
                "total": {"$sum": 1},
                "successful": {"$sum": {"$cond": [{"$eq": ["$success", True]}, 1, 0]}},
                "avg_prob": {"$avg": "$probability"}
            }},
            {"$sort": {"total": DESCENDING}},
            {"$limit": 10}
        ]
        coin_stats = list(db.signal_history.aggregate(coin_pipeline))
        
        return {
            "total_signals": total_signals,
            "successful_signals": successful,
            "failed_signals": failed,
            "pending_signals": pending,
            "success_rate": round(success_rate, 2),
            "max_gain": max_gain,
            "max_loss": max_loss,
            "avg_reward": round(avg_reward, 2) if avg_reward else 0,
            "coin_stats": coin_stats
        }
    except Exception as e:
        logger.error(f"❌ Dashboard stats hatası: {e}")
        return {
            "total_signals": 0,
            "successful_signals": 0,
            "failed_signals": 0,
            "pending_signals": 0,
            "success_rate": 0,
            "max_gain": 0,
            "max_loss": 0,
            "avg_reward": 0,
            "coin_stats": []
        }

def fetch_prune_candidates(cutoff_ts, min_samples, success_threshold):
    """Temizleme için aday kayıtları bul"""
    try:
        db = get_db()
        
        # MongoDB aggregation pipeline
        pipeline = [
            {"$match": {"created_at": {"$lte": cutoff_ts}}},
            {"$group": {
                "_id": {"coin": "$coin", "timeframe": "$timeframe"},
                "sample_count": {"$sum": 1},
                "success_count": {"$sum": {"$cond": [{"$eq": ["$success", True]}, 1, 0]}}
            }},
            {"$match": {"sample_count": {"$gte": min_samples}}}
        ]
        
        results = db.signal_history.aggregate(pipeline)
        
        candidates = []
        for r in results:
            sample_count = r["sample_count"]
            success_count = r["success_count"]
            success_rate = success_count / sample_count if sample_count > 0 else 0
            
            if success_rate < success_threshold:
                candidates.append((r["_id"]["coin"], r["_id"]["timeframe"]))
        
        return candidates
    except Exception as e:
        logger.error(f"❌ Prune candidates hatası: {e}")
        return []

def delete_records_by_coin_timeframe(coin, timeframe, cutoff_ts):
    """Belirli coin+timeframe için eski kayıtları sil"""
    try:
        db = get_db()
        
        # Silinecek kayıtların ID'lerini al
        cursor = db.signal_history.find({
            "coin": coin,
            "timeframe": timeframe,
            "created_at": {"$lte": cutoff_ts}
        }, {"_id": 1})
        
        ids = [str(doc["_id"]) for doc in cursor]
        
        # Sil
        result = db.signal_history.delete_many({
            "coin": coin,
            "timeframe": timeframe,
            "created_at": {"$lte": cutoff_ts}
        })
        
        logger.info(f"✅ Silindi: {result.deleted_count} kayıt ({coin}/{timeframe})")
        return ids
    except Exception as e:
        logger.error(f"❌ Delete records hatası: {e}")
        return []

def fetch_records_by_ids(ids):
    """Belirli ID'lere sahip kayıtları getir"""
    try:
        db = get_db()
        from bson.objectid import ObjectId
        
        # String ID'leri ObjectId'ye çevir
        object_ids = [ObjectId(id_str) for id_str in ids if ObjectId.is_valid(id_str)]
        
        cursor = db.signal_history.find({"_id": {"$in": object_ids}})
        
        records = []
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            records.append(doc)
        
        return records
    except Exception as e:
        logger.error(f"❌ Fetch by IDs hatası: {e}")
        return []

# Backward compatibility için dummy class'lar
class SessionLocal:
    """Dummy class - MongoDB kullanıyor"""
    pass

class SignalHistory:
    """Dummy class - MongoDB kullanıyor"""
    pass
