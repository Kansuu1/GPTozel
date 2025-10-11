# backend/notifier.py
import os, json, asyncio
import aiohttp
from data_sync import read_config

async def send_telegram_message_async(text: str, parse_mode="HTML", buttons=None):
    cfg = read_config()
    TELEGRAM_TOKEN = cfg.get("telegram_token") or os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT = cfg.get("telegram_chat_id") or os.getenv("TELEGRAM_CHAT_ID")
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        print("Telegram not configured, message:", text)
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as resp:
            return await resp.json()

def format_signal_message(rec: dict):
    txt = f"🔔 <b>{rec['coin']}</b> — <i>{rec['signal_type']}</i>\n"
    txt += f"Güvenilirlik: {rec['probability']:.2f}%  (Eşik: {rec['threshold_used']})\n"
    txt += f"Zaman Dilimi: {rec.get('timeframe')}\n"
    if rec.get("stop_loss"):
        txt += f"StopLoss önerisi: {rec.get('stop_loss')}\n"
    if rec.get("features") and rec['features'].get('price'):
        txt += f"Fiyat: ${rec['features']['price']:.4f}\n"
    txt += f"Zaman: {rec.get('created_at')}\n"
    return txt