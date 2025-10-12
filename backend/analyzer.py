# backend/analyzer.py
import os, asyncio, aiohttp
from datetime import datetime, timezone, timedelta
from cmc_client import CMCClient
from feature_store import build_features_from_quote
from model_stub import predict_signal_from_features
from db import insert_signal_record, init_db
from notifier import format_signal_message, send_telegram_message_async
from data_sync import read_config
from volatility_calculator import get_threshold
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
    max_concurrent = cfg.get("max_concurrent_coins", 20)
    
    # Coin başına özel ayarlar kullanılsın mı?
    use_coin_specific = cfg.get("use_coin_specific_settings", False)
    
    # Coin settings'i al (coin başına özel ayarlar)
    coin_settings_list = cfg.get("coin_settings", [])
    coin_settings_map = {cs["coin"]: cs for cs in coin_settings_list}
    
    # Eğer coin-specific mod aktifse, sadece aktif coinleri analiz et
    if use_coin_specific:
        active_coins = [cs["coin"] for cs in coin_settings_list if cs.get("active", True)]
        selected_coins = active_coins
        logger.info(f"Aktif coinler: {', '.join(active_coins)} ({len(active_coins)}/{len(coin_settings_list)})")
    
    # Global ayarlar
    global_threshold = cfg.get("threshold", 4)
    global_threshold_mode = cfg.get("threshold_mode", "dynamic")
    global_timeframe = cfg.get("timeframe", "24h")
    
    logger.info(f"Analiz modu: {'Coin-Bazlı Ayarlar' if use_coin_specific else 'Global Ayarlar'}")
    
    if not selected_coins:
        logger.warning("Seçili coin yok!")
        return
    
    async with aiohttp.ClientSession() as session:
        cmc = CMCClient(API_KEY)
        sem = asyncio.Semaphore(max_concurrent)
        
        async def handle_coin(sym):
            async with sem:
                try:
                    # Mod kontrolü: Coin-bazlı veya global ayarlar
                    if use_coin_specific and sym in coin_settings_map:
                        # Coin başına özel ayarlar aktif ve coin ayarı var
                        coin_config = coin_settings_map[sym]
                        timeframe = coin_config.get("timeframe")
                        manual_threshold = coin_config.get("threshold")
                        threshold_mode = coin_config.get("threshold_mode")
                        logger.info(f"[COIN-BAZLI] Analyzing {sym}: TF={timeframe}, threshold={manual_threshold}, mode={threshold_mode}")
                    else:
                        # Global ayarlar kullan
                        timeframe = global_timeframe
                        manual_threshold = global_threshold
                        threshold_mode = global_threshold_mode
                        logger.info(f"[GLOBAL] Analyzing {sym}: TF={timeframe}, threshold={manual_threshold}, mode={threshold_mode}")
                    
                    quote = await cmc.get_quote(session, sym)
                    features = build_features_from_quote(quote)
                    
                    # Dinamik veya manuel threshold kullan (coin başına)
                    threshold = get_threshold(features, threshold_mode, manual_threshold, timeframe)
                    
                    sig, prob, tp, sl, weight_desc = predict_signal_from_features(features, timeframe)
                    prob = float(prob)
                    
                    if sig and prob >= threshold:
                        rec = {
                            "coin": sym,
                            "symbol": sym,
                            "signal_type": sig,
                            "probability": prob,
                            "confidence_score": int(prob),
                            "threshold_used": threshold,
                            "timeframe": timeframe,
                            "features": features,
                            "stop_loss": sl,
                            "tp": tp,
                            "success": None,
                        }
                        rec_id = insert_signal_record(rec)
                        rec["id"] = rec_id
                        
                        # Türkiye saati (UTC+3)
                        turkey_time = datetime.now(timezone.utc) + timedelta(hours=3)
                        rec["created_at"] = turkey_time.strftime("%H:%M")
                        
                        msg = format_signal_message(rec)
                        await send_telegram_message_async(msg)
                        logger.info(f"Sinyal gönderildi: {sym} - {sig} - {prob:.2f}% (TF: {timeframe}, TP: ${tp}, SL: ${sl})")
                    else:
                        logger.debug(f"{sym}: Sinyal yok (prob={prob:.2f}%, threshold={threshold}, timeframe={timeframe})")
                        
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