# backend/db.py
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