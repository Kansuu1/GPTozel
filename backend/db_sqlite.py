# backend/db_sqlite.py - SQLite Version (Backup)
import os
from sqlalchemy import (create_engine, Column, Integer, String, Float, Boolean, JSON, TIMESTAMP, text)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from pathlib import Path

DATABASE_URL = os.getenv("DB_URL", "sqlite:///./data.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

class SignalHistory(Base):
    __tablename__ = "signal_history"
    id = Column(Integer, primary_key=True, index=True)
    coin = Column(String, index=True)
    symbol = Column(String, nullable=True)
    signal_type = Column(String)
    probability = Column(Float)
    confidence_score = Column(Integer, nullable=True)
    threshold_used = Column(Integer)
    timeframe = Column(String)
    features = Column(JSON, nullable=True)
    stop_loss = Column(Float, nullable=True)
    tp = Column(Float, nullable=True)
    success = Column(Boolean, nullable=True)
    reward = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class PerformanceAgg(Base):
    __tablename__ = "performance_agg"
    id = Column(Integer, primary_key=True, index=True)
    coin = Column(String, index=True)
    timeframe = Column(String, index=True)
    sample_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    avg_reward = Column(Float, default=0.0)
    last_updated = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

def init_db():
    Base.metadata.create_all(bind=engine)

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
