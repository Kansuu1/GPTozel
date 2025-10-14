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
    txt = f"📊 <b>MM TRADING BOT PRO  v2.1</b>\n"
    txt += f"🪙 <b>{rec['coin']}</b> — "
    
    # Sinyal tipine göre emoji
    if rec['signal_type'] == 'LONG':
        txt += f"<b>📈 LONG</b>\n"
    else:
        txt += f"<b>📉 SHORT</b>\n"
    
    # Fiyat bilgisi
    if rec.get("features") and rec['features'].get('price'):
        price = rec['features']['price']
        txt += f"💰 Giriş: <code>{format_price(price)}</code>\n"
    
    txt += f"💯 Güvenilirlik: <b>{rec['probability']:.2f}%</b> (Eşik: {rec['threshold_used']}%)\n"
    
    # Combined Signal Strength
    signal_strength = rec.get('signal_strength')
    if signal_strength:
        score = signal_strength.get('score', 0)
        fire_emoji = " 🔥" if score >= 80 else ""
        txt += f"📈 <b>Combined Signal Strength: {score:.0f}%{fire_emoji}</b>\n"
    
    # Gösterge Durumu
    txt += f"\n<b>🧠 Gösterge Durumu:</b>\n"
    
    # RSI
    if rec.get('rsi') is not None:
        rsi_signal = rec.get('rsi_signal', 'NEUTRAL')
        rsi_emoji = "🟢" if rsi_signal == "OVERSOLD" else "🔴" if rsi_signal == "OVERBOUGHT" else "⚪"
        txt += f"• RSI: {rec['rsi']:.2f} ({rsi_signal}) {rsi_emoji}\n"
    
    # MACD
    if rec.get('macd_signal'):
        macd_emoji = "📈" if rec['macd_signal'] == "BULLISH" else "📉" if rec['macd_signal'] == "BEARISH" else "➡️"
        txt += f"• MACD: {rec['macd_signal']} {macd_emoji}\n"
    
    # EMA
    if rec.get('ema9') and rec.get('ema21'):
        ema_signal = rec.get('ema_signal', 'NEUTRAL')
        ema_emoji = "🟢" if ema_signal == "BULLISH" else "🔴" if ema_signal == "BEARISH" else "⚪"
        txt += f"• EMA(9/21): {ema_signal} {ema_emoji}\n"
    
    # Trend Analizi (Golden/Death Cross)
    if rec.get('ema_cross'):
        cross_type = rec['ema_cross']
        if cross_type == "GOLDEN_CROSS":
            txt += f"• Trend Analizi: 🌟 Golden Cross (EMA50 > EMA200)\n"
        elif cross_type == "DEATH_CROSS":
            txt += f"• Trend Analizi: 💀 Death Cross (EMA50 < EMA200)\n"
    
    # Adaptive Mode ve Timeframe
    txt += f"\n<b>⚙️ Adaptive Mode:</b> "
    if rec.get('adaptive_timeframe_enabled'):
        txt += f"Aktif ✅\n"
        volatility = rec.get('volatility', 0)
        vol_text = "Yüksek" if volatility >= 6 else "Orta" if volatility >= 3 else "Düşük"
        txt += f"⏱ Timeframe: {rec.get('base_timeframe', '24h')} → {rec.get('timeframe')} (Volatilite {vol_text})\n"
    else:
        txt += f"Pasif\n"
        txt += f"⏱ Timeframe: {rec.get('timeframe')}\n"
    
    # Trend Ağırlığı
    if rec.get('trend_weight'):
        weight = rec['trend_weight']
        txt += f"⚖️ Trend Ağırlığı: {weight:+.0f}%\n"
    
    # TP ve SL
    txt += f"\n<b>🎯 Hedefler:</b>\n"
    if rec.get("tp"):
        txt += f"🎯 TP: <code>{format_price(rec['tp'])}</code>\n"
    if rec.get("stop_loss"):
        txt += f"🛡 SL: <code>{format_price(rec['stop_loss'])}</code>\n"
    
    # Risk/Reward
    if rec.get("tp") and rec.get("stop_loss") and rec.get("features") and rec['features'].get('price'):
        price = rec['features']['price']
        tp = rec['tp']
        sl = rec['stop_loss']
        
        if rec['signal_type'] == 'LONG':
            profit_percent = ((tp - price) / price) * 100
            loss_percent = ((price - sl) / price) * 100
        else:
            profit_percent = ((price - tp) / price) * 100
            loss_percent = ((sl - price) / price) * 100
        
        risk_reward = profit_percent / loss_percent if loss_percent > 0 else 0
        txt += f"📊 Risk/Reward: <b>1:{risk_reward:.1f}</b>\n"
    
    # Zaman - Türkiye UTC+3
    from datetime import datetime, timezone, timedelta
    turkey_tz = timezone(timedelta(hours=3))
    now = datetime.now(timezone.utc).astimezone(turkey_tz)
    txt += f"🕐 Zaman: {now.strftime('%d %B %H:%M')} (TR)\n"
    
    return txt