# backend/analyzer.py
import os, asyncio, aiohttp
from cmc_client import CMCClient
from feature_store import build_features_from_quote
from model_stub import predict_signal_from_features
from db import insert_signal_record, init_db
from notifier import format_signal_message, send_telegram_message_async
from data_sync import read_config
import logging

logger = logging.getLogger(__name__)

init_db()

async def analyze_cycle():
    """Ana analiz döngüsü - seçili coinleri analiz eder ve sinyal gönderir"""
    cfg = read_config()
    
    API_KEY = cfg.get("cmc_api_key") or os.getenv("CMC_API_KEY")
    if not API_KEY:
        logger.error("CMC API anahtarı bulunamadı!")
        return
    
    selected_coins = cfg.get("selected_coins", ["BTC", "ETH"])
    threshold = cfg.get("threshold", 75)
    max_concurrent = cfg.get("max_concurrent_coins", 20)
    
    if not selected_coins:
        logger.warning("Seçili coin yok!")
        return
    
    async with aiohttp.ClientSession() as session:
        cmc = CMCClient(API_KEY)
        sem = asyncio.Semaphore(max_concurrent)
        
        async def handle_coin(sym):
            async with sem:
                try:
                    quote = await cmc.get_quote(session, sym)
                    features = build_features_from_quote(quote)
                    sig, prob, tp, sl = predict_signal_from_features(features)
                    prob = float(prob)
                    
                    if sig and prob >= threshold:
                        rec = {
                            "coin": sym,
                            "symbol": sym,
                            "signal_type": sig,
                            "probability": prob,
                            "confidence_score": int(prob),
                            "threshold_used": threshold,
                            "timeframe": "1m/auto",
                            "features": features,
                            "stop_loss": sl,
                            "tp": tp,
                            "success": None,
                        }
                        rec_id = insert_signal_record(rec)
                        rec["id"] = rec_id
                        rec["created_at"] = "Az önce"
                        
                        msg = format_signal_message(rec)
                        await send_telegram_message_async(msg)
                        logger.info(f"Sinyal gönderildi: {sym} - {sig} - {prob:.2f}% (TP: ${tp}, SL: ${sl})")
                    else:
                        logger.debug(f"{sym}: Sinyal yok (prob={prob:.2f}%, threshold={threshold})")
                        
                except Exception as e:
                    logger.error(f"Coin işleme hatası {sym}: {e}")

        await asyncio.gather(*(handle_coin(c.strip().upper()) for c in selected_coins if c.strip()))

async def run_loop():
    """Ana döngü: Her 60 saniyede bir analiz çalıştırır"""
    logger.info("Analyzer loop başlatılıyor...")
    while True:
        try:
            await analyze_cycle()
        except Exception as e:
            logger.error(f"Analyzer cycle hatası: {e}")
        await asyncio.sleep(60)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_loop())