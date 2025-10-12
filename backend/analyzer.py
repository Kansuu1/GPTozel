# backend/analyzer.py
import os
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from cmc_client import CMCClient
from feature_store import build_features_from_quote
from model_stub import predict_signal_from_features
from db import insert_signal_record, init_db
from notifier import format_signal_message, send_telegram_message_async
from data_sync import read_config
from volatility_calculator import get_threshold
from price_history import get_recent_prices
from indicators import calculate_indicators
from price_alarms import create_price_alarm
from price_validator import get_validated_price, validate_price
import logging


# Global task tracking
running_tasks = {}
task_running = False

# Global coin data cache - server.py'den erişilebilir
coin_data_cache = {}


logger = logging.getLogger(__name__)

init_db()

def get_coin_from_cache(symbol: str):
    """Cache'den coin verisini al, yoksa None döndür"""
    if symbol in coin_data_cache:
        cache_entry = coin_data_cache[symbol]
        return cache_entry.get("data")
    return None

async def analyze_single_coin(symbol: str, quote: dict):
    """
    Tek bir coin için analiz yap ve gerekirse sinyal üret
    Bu fonksiyon fetch loop'tan her veri çekildikinde çağrılır
    """
    cfg = read_config()
    
    # Coin başına özel ayarlar
    use_coin_specific = cfg.get("use_coin_specific_settings", False)
    coin_settings = cfg.get("coin_settings", [])
    coin_settings_map = {cs["coin"]: cs for cs in coin_settings}
    
    # Global ayarlar
    global_threshold = cfg.get("threshold", 4)
    global_threshold_mode = cfg.get("threshold_mode", "dynamic")
    global_timeframe = cfg.get("timeframe", "24h")
    
    try:
        # Coin config al
        if use_coin_specific and symbol in coin_settings_map:
            coin_config = coin_settings_map[symbol]
            timeframe = coin_config.get("timeframe", "24h")
            manual_threshold = coin_config.get("threshold", 4)
            threshold_mode = coin_config.get("threshold_mode", "dynamic")
            logger.info(f"[{symbol}] Coin-bazlı analiz: TF={timeframe}, threshold={manual_threshold}, mode={threshold_mode}")
        else:
            timeframe = global_timeframe
            manual_threshold = global_threshold
            threshold_mode = global_threshold_mode
            logger.info(f"[{symbol}] Global ayarlarla analiz: TF={timeframe}, threshold={manual_threshold}, mode={threshold_mode}")
        
        # Feature extraction (sadece CMC verisi ile)
        features = build_features_from_quote(quote)
        
        # Threshold hesapla
        threshold = get_threshold(features, threshold_mode, manual_threshold, timeframe)
        
        # RSI ve MACD göstergelerini hesapla
        prices = get_recent_prices(symbol, count=50)
        indicators = {}
        if len(prices) >= 26:  # MACD için minimum
            indicators = calculate_indicators(prices)
            logger.info(f"[{symbol}] Göstergeler: RSI={indicators.get('rsi')}, MACD={indicators.get('macd_signal')}")
        
        # Sinyal tahmini
        sig, prob, tp, sl, weight_desc = predict_signal_from_features(features, timeframe)
        prob = float(prob)
        
        # RSI ve MACD ile sinyal doğruluğunu artır
        if indicators.get('rsi') is not None and indicators.get('macd_signal') is not None:
            rsi_signal = indicators['rsi_signal']
            macd_signal = indicators['macd_signal']
            
            # RSI oversold ve MACD bullish ise prob artır
            if sig == "LONG" and rsi_signal == "OVERSOLD" and macd_signal == "BULLISH":
                prob = min(prob * 1.2, 100)  # %20 artır
                logger.info(f"[{symbol}] RSI+MACD pozitif, prob artırıldı: {prob:.1f}%")
            
            # RSI overbought ve MACD bearish ise prob azalt
            elif sig == "LONG" and rsi_signal == "OVERBOUGHT" and macd_signal == "BEARISH":
                prob = prob * 0.8  # %20 azalt
                logger.info(f"[{symbol}] RSI+MACD negatif, prob azaltıldı: {prob:.1f}%")
        
        logger.info(f"[{symbol}] Analiz: Signal={sig}, Prob={prob:.1f}%, Threshold={threshold:.1f}%")
        
        # Threshold aşıldıysa sinyal üret
        if sig and prob >= threshold:
            rec = {
                "coin": symbol,
                "symbol": symbol,
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
            
            # RSI ve MACD değerlerini ekle
            if indicators:
                rec["rsi"] = indicators.get("rsi")
                rec["rsi_signal"] = indicators.get("rsi_signal")
                rec["macd"] = indicators.get("macd")
                rec["macd_signal"] = indicators.get("macd_signal")
            
            # DB'ye kaydet
            rec_id = insert_signal_record(rec)
            rec["id"] = rec_id
            
            # Türkiye saati
            turkey_time = datetime.now(timezone.utc) + timedelta(hours=3)
            rec["created_at"] = turkey_time.strftime("%H:%M")
            
            # Fiyat alarmı oluştur (sinyal giriş fiyatı için)
            entry_price = features.get("price", 0)
            if entry_price > 0:
                alarm_id = create_price_alarm(
                    coin=symbol,
                    target_price=entry_price,
                    alarm_type="target",
                    signal_id=str(rec_id),
                    signal_type=sig
                )
                if alarm_id:
                    rec["alarm_id"] = alarm_id
                    logger.info(f"🔔 [{symbol}] Fiyat alarmı oluşturuldu: {entry_price}$")
            
            # Telegram bildirimi gönder
            msg = format_signal_message(rec)
            
            try:
                result = await send_telegram_message_async(msg)
                if result and result.get('ok'):
                    logger.info(f"🚀 [{symbol}] Sinyal üretildi ve Telegram'a gönderildi! (Prob: {prob:.1f}%)")
                else:
                    logger.error(f"❌ [{symbol}] Telegram gönderimi başarısız: {result}")
            except Exception as e:
                logger.error(f"❌ [{symbol}] Telegram hatası: {e}")
                
            return True  # Sinyal üretildi
        else:
            logger.debug(f"[{symbol}] Threshold aşılmadı ({prob:.1f}% < {threshold:.1f}%), sinyal üretilmedi")
            return False  # Sinyal üretilmedi
            
    except Exception as e:
        logger.error(f"❌ [{symbol}] Analiz hatası: {e}")
        import traceback
        traceback.print_exc()
        return False

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
                    
                    # ÖNCELİKLE CACHE'DEN VERİ AL - En son çekilen veriyi kullan
                    quote = get_coin_from_cache(sym)
                    
                    # Cache'de yoksa API'den çek
                    if quote is None:
                        logger.debug(f"[{sym}] Cache'de bulunamadı, API'den çekiliyor...")
                        quote = await cmc.get_quote(session, sym)
                    else:
                        logger.debug(f"[{sym}] Cache'den alındı ✅")
                    
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
    """Ana döngü - backward compatibility için"""
    while True:
        try:
            await analyze_cycle()
        except Exception as e:
            logger.error(f"Analyzer cycle hatası: {e}")
        await asyncio.sleep(60)

async def analyze_with_intervals():
    """
    Fetch intervals kullanarak timeframe bazlı analiz
    Her timeframe için kendi interval'i ile döngü oluşturur
    """
    global task_running
    
    if task_running:
        logger.info("Interval-based analyzer zaten çalışıyor")
        return
    
    task_running = True
    cfg = read_config()
    
    # Fetch intervals al
    fetch_intervals = cfg.get("fetch_intervals", {
        "15m": 1, "1h": 2, "4h": 5, "12h": 10,
        "24h": 15, "7d": 30, "30d": 60
    })
    
    use_coin_specific = cfg.get("use_coin_specific_settings", False)
    
    if use_coin_specific:
        # Coin-bazlı mod: Her coin'in timeframe'i için ayrı task
        coin_settings_list = cfg.get("coin_settings", [])
        active_coins = [cs for cs in coin_settings_list if cs.get("active", True)]
        
        # Timeframe'lere göre grupla
        timeframe_groups = {}
        for cs in active_coins:
            tf = cs.get("timeframe", "24h")
            if tf not in timeframe_groups:
                timeframe_groups[tf] = []
            timeframe_groups[tf].append(cs)
        
        logger.info(f"Coin-bazlı mod: {len(timeframe_groups)} farklı timeframe tespit edildi")
        
        # Her timeframe için task oluştur
        tasks = []
        for timeframe, coins in timeframe_groups.items():
            interval = fetch_intervals.get(timeframe, 15)
            task = asyncio.create_task(
                analyze_timeframe_group(timeframe, coins, interval, use_coin_specific=True)
            )
            tasks.append(task)
            logger.info(f"Task başlatıldı: {timeframe} → {len(coins)} coin, interval: {interval}dk")
        
        # Tüm task'ları çalıştır
        await asyncio.gather(*tasks)
    else:
        # Global mod: Tüm coinler için tek bir timeframe
        global_timeframe = cfg.get("timeframe", "24h")
        interval = fetch_intervals.get(global_timeframe, 15)
        selected_coins = cfg.get("selected_coins", ["BTC", "ETH"])
        
        logger.info(f"Global mod: {global_timeframe}, interval: {interval}dk, {len(selected_coins)} coin")
        
        # Global mod için sürekli döngü
        while True:
            try:
                await analyze_cycle()
            except Exception as e:
                logger.error(f"Global analiz hatası: {e}")
            
            await asyncio.sleep(interval * 60)

async def analyze_timeframe_group(timeframe: str, coin_settings: list, interval_minutes: int, use_coin_specific: bool = False):
    """
    Belirli bir timeframe için sürekli analiz döngüsü
    """
    logger.info(f"[{timeframe}] Analiz döngüsü başladı (interval: {interval_minutes}dk)")
    
    while True:
        try:
            if use_coin_specific:
                # Coin-specific mode: sadece bu grup için analiz
                await analyze_coin_group(coin_settings, timeframe)
            else:
                # Global mode: tüm coinler için analiz
                await analyze_cycle()
            
        except Exception as e:
            logger.error(f"[{timeframe}] Analiz hatası: {e}")
        
        # Interval kadar bekle
        await asyncio.sleep(interval_minutes * 60)

async def analyze_coin_group(coin_settings: list, timeframe: str):
    """
    Belirli bir coin grubu için analiz yap
    """
    cfg = read_config()
    API_KEY = cfg.get("cmc_api_key") or os.getenv("CMC_API_KEY")
    
    if not API_KEY:
        logger.error("CMC API anahtarı bulunamadı!")
        return
    
    max_concurrent = cfg.get("max_concurrent_coins", 20)
    
    async with aiohttp.ClientSession() as session:
        cmc = CMCClient(API_KEY)
        sem = asyncio.Semaphore(max_concurrent)
        
        async def handle_coin(cs):
            async with sem:
                try:
                    coin_symbol = cs["coin"]
                    tf = cs.get("timeframe", timeframe)
                    manual_threshold = cs.get("threshold", 4)
                    threshold_mode = cs.get("threshold_mode", "dynamic")
                    
                    quote = await cmc.get_quote(session, coin_symbol)
                    features = build_features_from_quote(quote)
                    
                    threshold = get_threshold(features, threshold_mode, manual_threshold, tf)
                    sig, prob, tp, sl, weight_desc = predict_signal_from_features(features, tf)
                    prob = float(prob)
                    
                    if sig and prob >= threshold:
                        rec = {
                            "coin": coin_symbol,
                            "symbol": coin_symbol,
                            "signal_type": sig,
                            "probability": prob,
                            "confidence_score": int(prob),
                            "threshold_used": threshold,
                            "timeframe": tf,
                            "features": features,
                            "stop_loss": sl,
                            "tp": tp,
                            "created_at": datetime.now(timezone.utc)  # datetime object olmalı
                        }
                        
                        insert_signal_record(rec)
                        msg = format_signal_message(rec)
                        await send_telegram_message_async(msg)
                        logger.info(f"[{tf}] Sinyal: {coin_symbol} {sig} (prob={prob:.2f}%, threshold={threshold:.2f}%)")
                    
                except Exception as e:
                    logger.error(f"[{timeframe}] {cs.get('coin', 'UNKNOWN')} analiz hatası: {e}")
        
        tasks = [handle_coin(cs) for cs in coin_settings]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Config'e göre karar ver: interval-based veya eski mod
    cfg = read_config()
    use_intervals = cfg.get("use_fetch_intervals", True)  # Varsayılan: interval kullan
    
    if use_intervals:
        logger.info("🚀 Interval-based analyzer başlatılıyor...")
        asyncio.run(analyze_with_intervals())
    else:
        logger.info("⏱ Classic analyzer başlatılıyor (60s loop)...")
        asyncio.run(run_loop())