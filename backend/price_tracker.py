# backend/price_tracker.py
"""
Fiyat takip sistemi - TP/SL kontrolü
Her sinyal için güncel fiyatı kontrol eder ve başarı durumunu günceller
"""
import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from db import SessionLocal, SignalHistory
from cmc_client import CMCClient
from data_sync import read_config
import logging

logger = logging.getLogger(__name__)

class PriceTracker:
    def __init__(self):
        self.cfg = read_config()
        self.api_key = self.cfg.get("cmc_api_key")
        
    async def check_signal_status(self, signal: SignalHistory, current_price: float):
        """
        Sinyal durumunu kontrol et
        Returns: (status, reward)
        status: 'success', 'failed', 'pending'
        reward: kazanç/kayıp yüzdesi
        """
        if not signal.tp or not signal.stop_loss:
            return 'pending', 0.0
            
        entry_price = signal.features.get('price') if signal.features else None
        if not entry_price:
            return 'pending', 0.0
        
        if signal.signal_type == 'LONG':
            # LONG: TP yukarıda, SL aşağıda
            if current_price >= signal.tp:
                reward = ((signal.tp - entry_price) / entry_price) * 100
                return 'success', reward
            elif current_price <= signal.stop_loss:
                reward = ((signal.stop_loss - entry_price) / entry_price) * 100
                return 'failed', reward
        else:  # SHORT
            # SHORT: TP aşağıda, SL yukarıda
            if current_price <= signal.tp:
                reward = ((entry_price - signal.tp) / entry_price) * 100
                return 'success', reward
            elif current_price >= signal.stop_loss:
                reward = ((entry_price - signal.stop_loss) / entry_price) * 100
                return 'failed', reward
        
        return 'pending', 0.0
    
    async def track_all_signals(self):
        """
        Tüm pending sinyalleri kontrol et
        """
        if not self.api_key:
            logger.error("CMC API key bulunamadı!")
            return
        
        db = SessionLocal()
        try:
            # Sadece success = None olanları (pending) kontrol et
            pending_signals = db.query(SignalHistory).filter(
                SignalHistory.success == None
            ).all()
            
            if not pending_signals:
                logger.info("Kontrol edilecek pending sinyal yok")
                return
            
            logger.info(f"🔍 {len(pending_signals)} sinyal kontrol ediliyor...")
            
            async with aiohttp.ClientSession() as session:
                cmc = CMCClient(self.api_key)
                
                for signal in pending_signals:
                    try:
                        # Güncel fiyatı çek
                        quote = await cmc.get_quote(session, signal.coin)
                        data = quote["data"]
                        coin_data = data[list(data.keys())[0]]
                        current_price = coin_data["quote"]["USD"]["price"]
                        
                        # Durumu kontrol et
                        status, reward = await self.check_signal_status(signal, current_price)
                        
                        if status == 'success':
                            signal.success = True
                            signal.reward = reward
                            db.commit()
                            logger.info(f"✅ {signal.coin} TP'ye ulaştı! Kazanç: {reward:.2f}%")
                        elif status == 'failed':
                            signal.success = False
                            signal.reward = reward
                            db.commit()
                            logger.info(f"❌ {signal.coin} SL'e takıldı! Kayıp: {reward:.2f}%")
                        
                        await asyncio.sleep(0.5)  # Rate limiting
                        
                    except Exception as e:
                        logger.error(f"Fiyat kontrol hatası {signal.coin}: {e}")
                        continue
            
            logger.info("✅ Fiyat kontrolü tamamlandı")
            
        finally:
            db.close()

async def run_price_tracker():
    """Fiyat takip döngüsü - her 5 dakikada bir çalışır"""
    tracker = PriceTracker()
    while True:
        try:
            await tracker.track_all_signals()
        except Exception as e:
            logger.error(f"Price tracker hatası: {e}")
        await asyncio.sleep(300)  # 5 dakika bekle

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_price_tracker())
