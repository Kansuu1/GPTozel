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
from sqlalchemy import func, desc
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
    selected_coins: Optional[List[str]] = None
    timeframe: Optional[str] = None
    cmc_api_key: Optional[str] = None
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    allowed_user_ids: Optional[str] = None
    max_concurrent_coins: Optional[int] = None

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
    logger.info("Crypto Bot API başlatıldı")
    # Start analyzer in background
    asyncio.create_task(run_analyzer_loop())
    # Start cleanup scheduler in background
    asyncio.create_task(run_cleanup_scheduler())

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
