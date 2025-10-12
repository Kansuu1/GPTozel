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

# helper wrappers
def insert_signal_record(rec: dict):
    db = SessionLocal()
    try:
        obj = SignalHistory(**rec)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj.id
    finally:
        db.close()

def fetch_recent_signals(limit=100):
    db = SessionLocal()
    try:
        return db.query(SignalHistory).order_by(SignalHistory.created_at.desc()).limit(limit).all()
    finally:
        db.close()

def fetch_prune_candidates(cutoff_ts, min_samples, success_threshold):
    db = SessionLocal()
    try:
        # returns grouping coin+timeframe with ids
        sql = """
        SELECT coin, timeframe, COUNT(*) as sample_count,
            SUM(CASE WHEN success=1 THEN 1 ELSE 0 END) as success_count
        FROM signal_history
        WHERE created_at <= :cutoff
        GROUP BY coin, timeframe
        HAVING COUNT(*) >= :min_samples
        """
        rows = db.execute(text(sql), {"cutoff": cutoff_ts, "min_samples": min_samples}).fetchall()
        candidates = []
        for r in rows:
            sample_count = r[2]  # COUNT(*)
            success_count = r[3] or 0  # SUM(...)
            success_rate = success_count / sample_count if sample_count else 0
            if success_rate < success_threshold:
                candidates.append((r[0], r[1]))  # coin, timeframe
        return candidates
    finally:
        db.close()

def delete_records_by_coin_timeframe(coin, timeframe, cutoff_ts):
    db = SessionLocal()
    try:
        q = db.query(SignalHistory).filter(SignalHistory.coin==coin, SignalHistory.timeframe==timeframe, SignalHistory.created_at<=cutoff_ts)
        ids = [r.id for r in q.all()]
        q.delete(synchronize_session=False)
        db.commit()
        return ids
    finally:
        db.close()

def fetch_records_by_ids(ids):
    db = SessionLocal()
    try:
        return db.query(SignalHistory).filter(SignalHistory.id.in_(ids)).all()
    finally:
        db.close()