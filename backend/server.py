# backend/server.py
import os, asyncio, json
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
from dotenv import load_dotenv
import logging

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from data_sync import read_config, update_config
from notifier import send_telegram_message_async
from db import init_db, fetch_recent_signals, SessionLocal, SignalHistory
from analyzer import analyze_cycle
from sqlalchemy import func, desc, Integer
from datetime import datetime, timedelta

# Ensure DB and export dir exist
init_db()
EXPORT_DIR = os.getenv("EXPORT_DIR","/tmp/exports")
Path(EXPORT_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Crypto Bot Control API")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Admin token for protecting config-changing endpoints
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "cryptobot_admin_2024")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def require_admin(request: Request):
    if not ADMIN_TOKEN:
        return True
    auth = request.headers.get("x-admin-token")
    if auth != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Yetkisiz erişim")
    return True

class ConfigIn(BaseModel):
    threshold: Optional[int] = None
    threshold_mode: Optional[str] = None
    use_coin_specific_settings: Optional[bool] = None
    selected_coins: Optional[List[str]] = None
    timeframe: Optional[str] = None
    cmc_api_key: Optional[str] = None
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    allowed_user_ids: Optional[str] = None
    max_concurrent_coins: Optional[int] = None

class CoinSetting(BaseModel):
    coin: str
    timeframe: str
    threshold: float
    threshold_mode: str
    active: bool = True

class CoinSettingsUpdate(BaseModel):
    coin_settings: List[CoinSetting]

class FetchIntervals(BaseModel):
    intervals: dict  # {"15m": 1, "1h": 2, ...}

@app.get("/api/")
async def root():
    return {"message": "Crypto Bot API Çalışıyor", "status": "ok"}

@app.get("/api/config")
async def get_config():
    cfg = read_config()
    # Mask sensitive fields
    masked = dict(cfg)
    for k in ("cmc_api_key","telegram_token"):
        if k in masked and masked[k]:
            masked[k] = "*****"
    return JSONResponse(content=masked)

@app.post("/api/config")
async def post_config(payload: ConfigIn, request: Request):
    require_admin(request)
    cfg = read_config()
    updates = {}
    
    if payload.threshold is not None:
        updates["threshold"] = int(payload.threshold)
    if payload.threshold_mode is not None:
        mode = payload.threshold_mode.strip().lower()
        if mode in ["manual", "dynamic"]:
            updates["threshold_mode"] = mode
    if payload.use_coin_specific_settings is not None:
        updates["use_coin_specific_settings"] = bool(payload.use_coin_specific_settings)
    if payload.selected_coins is not None:
        updates["selected_coins"] = [c.strip().upper() for c in payload.selected_coins if c.strip()]
    if payload.timeframe is not None:
        updates["timeframe"] = payload.timeframe.strip()
    if payload.cmc_api_key is not None and payload.cmc_api_key != "*****":
        updates["cmc_api_key"] = payload.cmc_api_key.strip()
    if payload.telegram_token is not None and payload.telegram_token != "*****":
        updates["telegram_token"] = payload.telegram_token.strip()
    if payload.telegram_chat_id is not None:
        updates["telegram_chat_id"] = str(payload.telegram_chat_id).strip()
    if payload.allowed_user_ids is not None:
        updates["allowed_user_ids"] = payload.allowed_user_ids.strip()
    if payload.max_concurrent_coins is not None:
        updates["max_concurrent_coins"] = int(payload.max_concurrent_coins)
    
    if updates:
        cfg = update_config(updates)
    
    # Mask for response
    response_cfg = {k: (v if k not in ('cmc_api_key','telegram_token') else ("*****" if v else None)) for k,v in cfg.items()}
    return {"status":"ok", "config": response_cfg}

@app.post("/api/test_telegram")
async def test_telegram(request: Request):
    require_admin(request)
    cfg = read_config()
    token = cfg.get("telegram_token") or os.getenv("TELEGRAM_BOT_TOKEN")
    chat = cfg.get("telegram_chat_id") or os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat:
        raise HTTPException(status_code=400, detail="Telegram yapılandırması eksik")
    
    msg = "🔔 Test mesajı: Telegram entegrasyonu başarılı! (Crypto Bot)"
    
    import aiohttp
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat, "text": msg}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as resp:
            data = await resp.json()
            if not data.get("ok"):
                raise HTTPException(status_code=500, detail=f"Telegram API hatası: {data}")
    
    return {"status":"ok", "detail":"Test mesajı gönderildi"}

@app.get("/api/coins")
async def get_coins():
    cfg = read_config()
    return {
        "selected_coins": cfg.get("selected_coins", []),
        "max_concurrent_coins": cfg.get("max_concurrent_coins", 20),
        "threshold": cfg.get("threshold", 75)
    }

@app.post("/api/coins/select")
async def select_coins(payload: dict, request: Request):
    require_admin(request)
    selected = payload.get("selected_coins", [])
    cfg = update_config({"selected_coins": [c.strip().upper() for c in selected if c.strip()]})
    return {"status": "ok", "selected_coins": cfg.get("selected_coins")}


@app.get("/api/coin-settings")
async def get_coin_settings():
    """Coin başına ayarları getir"""
    cfg = read_config()
    coin_settings = cfg.get("coin_settings", [])
    selected_coins = cfg.get("selected_coins", [])
    
    # Eğer coin_settings boşsa veya yeni coinler eklendiyse varsayılan ayarlarla doldur
    existing_coins = {cs["coin"] for cs in coin_settings}
    default_timeframe = cfg.get("timeframe", "24h")
    default_threshold = cfg.get("threshold", 4)
    default_mode = cfg.get("threshold_mode", "dynamic")
    
    for coin in selected_coins:
        if coin not in existing_coins:
            coin_settings.append({
                "coin": coin,
                "timeframe": default_timeframe,
                "threshold": float(default_threshold),
                "threshold_mode": default_mode,
                "active": True
            })
    
    # TÜM coin_settings'i döndür (filtreleme yapma)
    # Frontend'de zaten sadece aktif olanlar gösterilecek
    return {"coin_settings": coin_settings}

@app.post("/api/coin-settings")
async def update_coin_settings(payload: CoinSettingsUpdate, request: Request):
    """Coin başına ayarları güncelle"""
    require_admin(request)
    
    cfg = read_config()
    
    # Yeni ayarları doğrula ve formatla
    new_settings = []
    coin_list = []
    for setting in payload.coin_settings:
        coin_symbol = setting.coin.strip().upper()
        new_settings.append({
            "coin": coin_symbol,
            "timeframe": setting.timeframe.strip(),
            "threshold": float(setting.threshold),
            "threshold_mode": setting.threshold_mode.strip().lower(),
            "active": bool(setting.active)
        })
        coin_list.append(coin_symbol)
    
    # Config'i güncelle - hem coin_settings hem de selected_coins
    cfg = update_config({
        "coin_settings": new_settings,
        "selected_coins": coin_list
    })
    
    logger.info(f"🔄 Coin ayarları güncellendi. Değişiklikler backend restart'ta uygulanacak.")
    
    return {
        "status": "ok",
        "message": f"{len(new_settings)} coin ayarı güncellendi",
        "coin_settings": new_settings,
        "selected_coins": coin_list
    }


@app.get("/api/fetch-intervals")
async def get_fetch_intervals():
    """Timeframe bazlı veri çekme sıklığını getir"""
    cfg = read_config()
    
    # Varsayılan intervals
    default_intervals = {
        "15m": 1,
        "1h": 2,
        "4h": 5,
        "12h": 10,
        "24h": 15,
        "7d": 30,
        "30d": 60
    }
    
    intervals = cfg.get("fetch_intervals", default_intervals)
    return {"fetch_intervals": intervals}

@app.post("/api/fetch-intervals")
async def update_fetch_intervals(payload: FetchIntervals, request: Request):
    """Timeframe bazlı veri çekme sıklığını güncelle"""
    require_admin(request)
    
    # Validate intervals
    valid_intervals = {}
    for timeframe, minutes in payload.intervals.items():
        if isinstance(minutes, (int, float)) and minutes > 0:
            valid_intervals[timeframe] = int(minutes)
    
    if not valid_intervals:
        raise HTTPException(status_code=400, detail="Geçerli interval değeri bulunamadı")
    
    # Update config
    cfg = update_config({"fetch_intervals": valid_intervals})
    
    # Analyzer'ı yeniden başlat (yeni interval'lerle)
    logger.info("🔄 Interval değişti, analyzer yeniden başlatılıyor...")
    
    # Not: Task'ları iptal edip yeniden başlatmak için
    # restart_analyzer fonksiyonu ekleyeceğiz
    
    return {
        "status": "ok",
        "message": f"{len(valid_intervals)} timeframe interval güncellendi. Değişiklikler backend restart'ta uygulanacak.",
        "fetch_intervals": valid_intervals,
        "note": "Backend'i restart ederek değişiklikleri uygulayın"
    }



@app.post("/api/start-interval-analyzer")
async def start_interval_analyzer(request: Request):
    """Interval-based analyzer başlat"""
    require_admin(request)
    
    try:
        from analyzer import analyze_with_intervals
        asyncio.create_task(analyze_with_intervals())
        return {"status": "ok", "message": "Interval-based analyzer başlatıldı"}
    except Exception as e:
        logger.error(f"Analyzer başlatma hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/restart")
async def restart_backend(request: Request):
    """Backend'i yeniden başlat (analyzer'ı yeniden başlatır)"""
    require_admin(request)
    
    logger.info("🔄 Backend restart komutu alındı")
    
    # Supervisor ile restart
    import subprocess
    try:
        subprocess.Popen(["sudo", "supervisorctl", "restart", "backend"])
        return {"status": "ok", "message": "Backend yeniden başlatılıyor..."}
    except Exception as e:
        logger.error(f"Restart hatası: {e}")
        raise HTTPException(status_code=500, detail="Restart başarısız")


    
    # Config'i güncelle - hem coin_settings hem de selected_coins
    cfg = update_config({
        "coin_settings": new_settings,
        "selected_coins": coin_list
    })
    
    logger.info(f"🔄 Coin ayarları güncellendi. Değişiklikler backend restart'ta uygulanacak.")
    
    return {
        "status": "ok",
        "message": f"{len(new_settings)} coin ayarı güncellendi. Değişiklikler backend restart'ta uygulanacak.",
        "coin_settings": new_settings,
        "selected_coins": coin_list,
        "note": "Backend'i restart ederek değişiklikleri uygulayın"
    }


@app.get("/api/signals")
async def get_signals(limit: int = 50):
    recs = fetch_recent_signals(limit)
    out = []
    for r in recs:
        out.append({
            "id": r.id,
            "coin": r.coin,
            "signal_type": r.signal_type,
            "probability": r.probability,
            "threshold_used": r.threshold_used,
            "timeframe": r.timeframe,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "features": r.features,
            "tp": r.tp,
            "stop_loss": r.stop_loss
        })
    return {"signals": out}


@app.get("/api/performance-dashboard")
async def get_performance_dashboard():
    """Performance dashboard verileri"""
    db = SessionLocal()
    try:
        # Toplam sinyal sayısı
        total_signals = db.query(SignalHistory).count()
        
        # Başarılı ve başarısız sinyaller
        successful_signals = db.query(SignalHistory).filter(SignalHistory.success == True).count()
        failed_signals = db.query(SignalHistory).filter(SignalHistory.success == False).count()
        pending_signals = db.query(SignalHistory).filter(SignalHistory.success == None).count()
        
        # Ortalama başarı yüzdesi
        success_rate = (successful_signals / total_signals * 100) if total_signals > 0 else 0
        
        # En yüksek kazanç ve kayıp
        max_gain = db.query(func.max(SignalHistory.reward)).filter(SignalHistory.reward != None).scalar() or 0
        max_loss = db.query(func.min(SignalHistory.reward)).filter(SignalHistory.reward != None).scalar() or 0
        
        # Ortalama reward
        avg_reward = db.query(func.avg(SignalHistory.reward)).filter(SignalHistory.reward != None).scalar() or 0
        
        # Top 5 kazançlı sinyal
        top_profitable = db.query(SignalHistory).filter(
            SignalHistory.reward != None,
            SignalHistory.reward > 0
        ).order_by(desc(SignalHistory.reward)).limit(5).all()
        
        top_profitable_list = [{
            "id": s.id,
            "coin": s.coin,
            "signal_type": s.signal_type,
            "reward": round(s.reward, 2) if s.reward else 0,
            "probability": round(s.probability, 2) if s.probability else 0,
            "timeframe": s.timeframe,
            "created_at": s.created_at.isoformat() if s.created_at else None
        } for s in top_profitable]
        
        # Son 6 aylık sinyal dağılımı
        six_months_ago = datetime.now() - timedelta(days=180)
        monthly_signals = db.query(
            func.strftime('%Y-%m', SignalHistory.created_at).label('month'),
            func.count(SignalHistory.id).label('count')
        ).filter(
            SignalHistory.created_at >= six_months_ago
        ).group_by('month').order_by('month').all()
        
        monthly_data = [{"month": m[0], "count": m[1]} for m in monthly_signals]
        
        # Coin bazlı performans (başarı oranı)
        coin_performance = db.query(
            SignalHistory.coin,
            func.count(SignalHistory.id).label('total'),
            func.sum(func.cast(SignalHistory.success, Integer)).label('successful')
        ).group_by(SignalHistory.coin).all()
        
        coin_stats = []
        for cp in coin_performance:
            total = cp[1]
            successful = cp[2] or 0
            success_rate_coin = (successful / total * 100) if total > 0 else 0
            coin_stats.append({
                "coin": cp[0],
                "total_signals": total,
                "successful": successful,
                "success_rate": round(success_rate_coin, 2)
            })
        
        # En iyi performans gösteren coinler (başarı oranına göre)
        coin_stats_sorted = sorted(coin_stats, key=lambda x: x['success_rate'], reverse=True)[:10]
        
        # Signal type dağılımı (LONG vs SHORT)
        signal_type_dist = db.query(
            SignalHistory.signal_type,
            func.count(SignalHistory.id).label('count')
        ).group_by(SignalHistory.signal_type).all()
        
        signal_types = [{"type": st[0], "count": st[1]} for st in signal_type_dist]
        
        return {
            "summary": {
                "total_signals": total_signals,
                "successful_signals": successful_signals,
                "failed_signals": failed_signals,
                "pending_signals": pending_signals,
                "success_rate": round(success_rate, 2),
                "max_gain": round(max_gain, 2) if max_gain else 0,
                "max_loss": round(max_loss, 2) if max_loss else 0,
                "avg_reward": round(avg_reward, 2) if avg_reward else 0
            },
            "top_profitable": top_profitable_list,
            "monthly_signals": monthly_data,
            "coin_performance": coin_stats_sorted,
            "signal_type_distribution": signal_types
        }
    except Exception as e:
        logger.error(f"Performance dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/analyze_now")
async def analyze_now(background_tasks: BackgroundTasks, request: Request):
    """Manuel analiz tetikleme"""
    require_admin(request)
    background_tasks.add_task(analyze_cycle)
    return {"status": "ok", "message": "Analiz başlatıldı"}

@app.delete("/api/signals/{signal_id}")
async def delete_signal(signal_id: int, request: Request):
    """Tek bir sinyali sil"""
    require_admin(request)
    from db import SessionLocal, SignalHistory
    db = SessionLocal()
    try:
        signal = db.query(SignalHistory).filter(SignalHistory.id == signal_id).first()
        if not signal:
            raise HTTPException(status_code=404, detail="Sinyal bulunamadı")
        db.delete(signal)
        db.commit()
        return {"status": "ok", "message": f"Sinyal {signal_id} silindi"}
    finally:
        db.close()

@app.post("/api/signals/clear_all")
async def clear_all_signals(request: Request):
    """Tüm sinyalleri sil"""
    require_admin(request)
    from db import SessionLocal, SignalHistory
    db = SessionLocal()
    try:
        count = db.query(SignalHistory).count()
        db.query(SignalHistory).delete()
        db.commit()
        return {"status": "ok", "message": f"{count} sinyal silindi"}
    finally:
        db.close()

@app.post("/api/signals/clear_failed")
async def clear_failed_signals(request: Request):
    """Başarısız sinyalleri sil"""
    require_admin(request)
    from db import SessionLocal, SignalHistory
    db = SessionLocal()
    try:
        failed = db.query(SignalHistory).filter(SignalHistory.success == False).all()
        count = len(failed)
        db.query(SignalHistory).filter(SignalHistory.success == False).delete()
        db.commit()
        return {"status": "ok", "message": f"{count} başarısız sinyal silindi"}
    finally:
        db.close()

@app.get("/api/exports/{filename}")
async def download_export(filename: str):
    p = os.path.join(EXPORT_DIR, filename)
    if not os.path.exists(p):
        raise HTTPException(status_code=404, detail="Dosya bulunamadı")
    return FileResponse(p, media_type="application/octet-stream", filename=filename)

@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında çalışacak"""
    logger.info("Veritabanı başlatılıyor...")
    init_db()
    logger.info("✅ Veritabanı hazır")
    
    # Eski sinyalleri temizle
    from cleanup_scheduler import start_scheduler as start_cleanup
    asyncio.create_task(start_cleanup())
    
    # Price tracker'ı başlat
    try:
        from price_tracker import start_price_tracking
        asyncio.create_task(start_price_tracking())
    except ImportError:
        logger.warning("Price tracker bulunamadı")
    
    # Analyzer'ı başlat (interval-based veya classic)
    from analyzer import analyze_with_intervals, run_loop
    from data_sync import read_config
    
    cfg = read_config()
    use_intervals = cfg.get("use_fetch_intervals", True)
    
    if use_intervals:
        logger.info("🚀 Interval-based analyzer başlatılıyor...")
        asyncio.create_task(analyze_with_intervals())
    else:
        logger.info("⏱ Classic analyzer başlatılıyor...")
        asyncio.create_task(run_loop())

async def run_analyzer_loop():
    """Background analyzer loop"""
    from analyzer import run_loop
    await run_loop()

async def run_cleanup_scheduler():
    """Background cleanup scheduler"""
    from cleanup_scheduler import start_scheduler
    await start_scheduler()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
