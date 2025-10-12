# backend/notifier.py
import os, json, asyncio
import aiohttp
from data_sync import read_config
import logging

logger = logging.getLogger(__name__)

async def send_telegram_message_async(text: str, parse_mode="HTML", buttons=None):
    cfg = read_config()
    TELEGRAM_TOKEN = cfg.get("telegram_token") or os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT = cfg.get("telegram_chat_id") or os.getenv("TELEGRAM_CHAT_ID")
    
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        logger.error(f"❌ Telegram config eksik! Token: {bool(TELEGRAM_TOKEN)}, Chat: {bool(TELEGRAM_CHAT)}")
        return {"ok": False, "error": "Config eksik"}
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    if buttons:
        payload["reply_markup"] = json.dumps({"inline_keyboard": buttons})
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload) as resp:
                result = await resp.json()
                if result.get('ok'):
                    logger.debug(f"✅ Telegram mesajı gönderildi")
                else:
                    logger.error(f"❌ Telegram API hatası: {result}")
                return result
    except Exception as e:
        logger.error(f"❌ Telegram gönderme hatası: {e}")
        return {"ok": False, "error": str(e)}

def format_price(price):
    """
    Fiyatı akıllıca formatla
    - Büyük fiyatlar (>=1): 2 ondalık (örn: $1,234.56)
    - Orta fiyatlar (0.01-1): 4 ondalık (örn: $0.1234)
    - Küçük fiyatlar (0.00001-0.01): 6 ondalık (örn: $0.001234)
    - Çok küçük (<0.00001): 8 ondalık (örn: $0.00000123)
    """
    if price >= 1:
        return f"${price:,.2f}"
    elif price >= 0.01:
        return f"${price:.4f}"
    elif price >= 0.00001:
        return f"${price:.6f}"
    else:
        # Çok küçük değerler için 8-10 ondalık
        return f"${price:.10f}".rstrip('0').rstrip('.')

def format_signal_message(rec: dict):
    txt = f"📊 <b>MM TRADING BOT PRO</b>\n\n"
    txt += f"🪙 <b>{rec['coin']}</b> — "
    
    # Sinyal tipine göre emoji
    if rec['signal_type'] == 'LONG':
        txt += f"<b>📈 LONG</b>\n"
    else:
        txt += f"<b>📉 SHORT</b>\n"
    
    # Fiyat bilgisi
    if rec.get("features") and rec['features'].get('price'):
        price = rec['features']['price']
        txt += f"💰 Giriş Fiyatı: <code>{format_price(price)}</code>\n"
    
    txt += f"💯 Güvenilirlik: <b>{rec['probability']:.2f}%</b>  (Eşik: {rec['threshold_used']}%)\n"
    txt += f"⏱ Zaman Dilimi: {rec.get('timeframe')}\n\n"
    
    # TP ve SL önerileri
    txt += f"<b>🎯 Hedefler:</b>\n"
    if rec.get("tp"):
        tp = rec.get('tp')
        txt += f"✅ Take Profit (TP): <code>{format_price(tp)}</code>\n"
    if rec.get("stop_loss"):
        sl = rec.get('stop_loss')
        txt += f"🛡 Stop Loss (SL): <code>{format_price(sl)}</code>\n"
    
    # Risk/Reward hesaplama
    if rec.get("tp") and rec.get("stop_loss") and rec.get("features") and rec['features'].get('price'):
        price = rec['features']['price']
        tp = rec.get('tp')
        sl = rec.get('stop_loss')
        
        if rec['signal_type'] == 'LONG':
            profit_percent = ((tp - price) / price) * 100
            loss_percent = ((price - sl) / price) * 100
        else:
            profit_percent = ((price - tp) / price) * 100
            loss_percent = ((sl - price) / price) * 100
        
        risk_reward = profit_percent / loss_percent if loss_percent > 0 else 0
        txt += f"\n📊 Potansiyel Kazanç: <b>+{profit_percent:.2f}%</b>\n"
        txt += f"📊 Potansiyel Kayıp: <b>-{loss_percent:.2f}%</b>\n"
        txt += f"⚖️ Risk/Reward: <b>1:{risk_reward:.1f}</b>\n"
    
    txt += f"\n🕐 Zaman: {rec.get('created_at')} (TR)\n"
    return txt