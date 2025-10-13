# backend/signal_tracker.py
"""
Sinyal Performans İzleme Servisi
TP/SL kontrolü ve status güncelleme
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from db_mongodb import get_db
from data_sync import get_latest_coin_data

logger = logging.getLogger(__name__)


def check_signal_status(signal: Dict) -> Dict:
    """
    Tek bir sinyal için TP/SL kontrolü yap
    
    Returns:
        Updated signal dict with new status and profit_loss_percent
    """
    coin = signal.get("coin")
    signal_type = signal.get("signal_type")
    entry_price = signal.get("features", {}).get("price", 0)
    tp = signal.get("tp", 0)
    sl = signal.get("stop_loss", 0)
    signal_timestamp = signal.get("signal_timestamp") or signal.get("created_at")
    
    if not all([coin, entry_price, tp, sl, signal_timestamp]):
        logger.warning(f"[{coin}] Eksik veri, status güncellenemedi")
        return signal
    
    # Güncel fiyatı al
    try:
        coin_data = get_latest_coin_data(coin)
        if not coin_data:
            return signal
        
        current_price = coin_data.get("price", 0)
        if current_price == 0:
            return signal
        
    except Exception as e:
        logger.error(f"[{coin}] Fiyat alınamadı: {e}")
        return signal
    
    # Status güncelleme
    new_status = signal.get("signal_status", "active")
    profit_loss = 0.0
    
    # TP kontrolü
    if signal_type == "LONG" and current_price >= tp:
        new_status = "hit_tp"
        profit_loss = ((tp - entry_price) / entry_price) * 100
        logger.info(f"✅ [{coin}] TP HIT! Entry: ${entry_price:.4f} → TP: ${tp:.4f} (+{profit_loss:.2f}%)")
        
    elif signal_type == "SHORT" and current_price <= tp:
        new_status = "hit_tp"
        profit_loss = ((entry_price - tp) / entry_price) * 100
        logger.info(f"✅ [{coin}] TP HIT! Entry: ${entry_price:.4f} → TP: ${tp:.4f} (+{profit_loss:.2f}%)")
    
    # SL kontrolü
    elif signal_type == "LONG" and current_price <= sl:
        new_status = "hit_sl"
        profit_loss = ((sl - entry_price) / entry_price) * 100
        logger.info(f"🛑 [{coin}] SL HIT! Entry: ${entry_price:.4f} → SL: ${sl:.4f} ({profit_loss:.2f}%)")
        
    elif signal_type == "SHORT" and current_price >= sl:
        new_status = "hit_sl"
        profit_loss = ((entry_price - sl) / entry_price) * 100
        logger.info(f"🛑 [{coin}] SL HIT! Entry: ${entry_price:.4f} → SL: ${sl:.4f} ({profit_loss:.2f}%)")
    
    # Expired kontrolü (24 saat geçti mi?)
    if new_status == "active" and signal_timestamp:
        if isinstance(signal_timestamp, str):
            signal_timestamp = datetime.fromisoformat(signal_timestamp.replace('Z', '+00:00'))
        
        now = datetime.now(timezone.utc)
        time_diff = now - signal_timestamp
        
        if time_diff > timedelta(hours=24):
            new_status = "expired"
            # Current price ile entry arasındaki farkı hesapla
            if signal_type == "LONG":
                profit_loss = ((current_price - entry_price) / entry_price) * 100
            else:
                profit_loss = ((entry_price - current_price) / entry_price) * 100
            logger.info(f"⏰ [{coin}] Signal EXPIRED (24h). P/L: {profit_loss:.2f}%")
    
    # Güncelleme gerekiyorsa
    if new_status != signal.get("signal_status"):
        signal["signal_status"] = new_status
        signal["profit_loss_percent"] = round(profit_loss, 2)
        return signal
    
    return None  # Güncelleme yok


def update_all_signals() -> Dict[str, int]:
    """
    Tüm aktif sinyalleri kontrol edip güncelle
    
    Returns:
        Stats: {updated: int, hit_tp: int, hit_sl: int, expired: int}
    """
    db = get_db()
    
    # Sadece aktif sinyalleri getir
    active_signals = list(db.signal_history.find({
        "signal_status": "active"
    }))
    
    stats = {
        "checked": len(active_signals),
        "updated": 0,
        "hit_tp": 0,
        "hit_sl": 0,
        "expired": 0
    }
    
    for signal in active_signals:
        updated_signal = check_signal_status(signal)
        
        if updated_signal:
            # MongoDB'de güncelle
            result = db.signal_history.update_one(
                {"_id": signal["_id"]},
                {"$set": {
                    "signal_status": updated_signal["signal_status"],
                    "profit_loss_percent": updated_signal["profit_loss_percent"]
                }}
            )
            
            if result.modified_count > 0:
                stats["updated"] += 1
                
                if updated_signal["signal_status"] == "hit_tp":
                    stats["hit_tp"] += 1
                elif updated_signal["signal_status"] == "hit_sl":
                    stats["hit_sl"] += 1
                elif updated_signal["signal_status"] == "expired":
                    stats["expired"] += 1
    
    logger.info(f"📊 Signal Tracking: {stats['checked']} kontrol edildi, {stats['updated']} güncellendi (TP:{stats['hit_tp']}, SL:{stats['hit_sl']}, Expired:{stats['expired']})")
    
    return stats


def get_signal_statistics() -> Dict:
    """
    Sinyal istatistiklerini getir
    """
    db = get_db()
    
    total = db.signal_history.count_documents({})
    active = db.signal_history.count_documents({"signal_status": "active"})
    hit_tp = db.signal_history.count_documents({"signal_status": "hit_tp"})
    hit_sl = db.signal_history.count_documents({"signal_status": "hit_sl"})
    expired = db.signal_history.count_documents({"signal_status": "expired"})
    
    # Win rate hesapla
    closed_signals = hit_tp + hit_sl
    win_rate = (hit_tp / closed_signals * 100) if closed_signals > 0 else 0
    
    # Ortalama kar/zarar
    closed_results = list(db.signal_history.find({
        "signal_status": {"$in": ["hit_tp", "hit_sl"]},
        "profit_loss_percent": {"$exists": True}
    }))
    
    avg_profit = sum(s.get("profit_loss_percent", 0) for s in closed_results) / len(closed_results) if closed_results else 0
    
    return {
        "total": total,
        "active": active,
        "hit_tp": hit_tp,
        "hit_sl": hit_sl,
        "expired": expired,
        "win_rate": round(win_rate, 2),
        "avg_profit_loss": round(avg_profit, 2)
    }
