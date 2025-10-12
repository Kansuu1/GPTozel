# backend/cleanup_scheduler.py
"""
Otomatik temizlik scheduler
- Günlük 23:59: SL'e takılan sinyalleri sil
- 7 gün: TP/SL'e ulaşmayanları sil
- 28 gün: Top 100 başarılı sinyal hariç geri kalanı sil
"""
import asyncio
import schedule
import time
from datetime import datetime, timezone, timedelta
from db import SessionLocal, SignalHistory
from price_tracker import PriceTracker
import logging

logger = logging.getLogger(__name__)

class CleanupScheduler:
    def __init__(self):
        self.last_cleanup_date = None
        
    async def daily_cleanup(self):
        """
        Günlük temizlik (23:59)
        - SL'e takılanları sil
        - 7 günden eski pending sinyalleri sil
        """
        logger.info("🧹 Günlük temizlik başlatılıyor...")
        
        db = SessionLocal()
        try:
            # 1. SL'e takılanları sil
            failed_signals = db.query(SignalHistory).filter(
                SignalHistory.success == False
            ).all()
            
            if failed_signals:
                failed_ids = [s.id for s in failed_signals]
                db.query(SignalHistory).filter(
                    SignalHistory.id.in_(failed_ids)
                ).delete(synchronize_session=False)
                db.commit()
                logger.info(f"❌ {len(failed_signals)} başarısız sinyal silindi")
            
            # 2. 7 günden eski pending sinyalleri sil
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            old_pending = db.query(SignalHistory).filter(
                SignalHistory.success == None,
                SignalHistory.created_at < seven_days_ago
            ).all()
            
            if old_pending:
                old_ids = [s.id for s in old_pending]
                db.query(SignalHistory).filter(
                    SignalHistory.id.in_(old_ids)
                ).delete(synchronize_session=False)
                db.commit()
                logger.info(f"⏰ {len(old_pending)} eski pending sinyal silindi (7 gün)")
            
            logger.info("✅ Günlük temizlik tamamlandı")
            
        except Exception as e:
            logger.error(f"Günlük temizlik hatası: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def monthly_cleanup(self):
        """
        Aylık temizlik (28 gün)
        - Top 100 başarılı sinyal sakla
        - Geri kalanı sil
        """
        logger.info("🗓 Aylık temizlik başlatılıyor...")
        
        db = SessionLocal()
        try:
            # 28 günden eski başarılı sinyaller
            twenty_eight_days_ago = datetime.now(timezone.utc) - timedelta(days=28)
            old_successful = db.query(SignalHistory).filter(
                SignalHistory.success == True,
                SignalHistory.created_at < twenty_eight_days_ago
            ).order_by(SignalHistory.reward.desc()).all()
            
            if len(old_successful) > 100:
                # Top 100 hariç geri kalanı sil
                to_delete = old_successful[100:]
                delete_ids = [s.id for s in to_delete]
                
                db.query(SignalHistory).filter(
                    SignalHistory.id.in_(delete_ids)
                ).delete(synchronize_session=False)
                db.commit()
                
                logger.info(f"🏆 Top 100 başarılı sinyal korundu")
                logger.info(f"🗑 {len(to_delete)} eski başarılı sinyal silindi")
            else:
                logger.info(f"ℹ️ 28 günden eski sadece {len(old_successful)} başarılı sinyal var (Top 100'den az)")
            
            logger.info("✅ Aylık temizlik tamamlandı")
            
        except Exception as e:
            logger.error(f"Aylık temizlik hatası: {e}")
            db.rollback()
        finally:
            db.close()
    
    def check_missed_cleanup(self):
        """
        Sistem kapalıyken kaçırılan temizlikleri kontrol et
        """
        today = datetime.now(timezone.utc).date()
        
        if self.last_cleanup_date is None or self.last_cleanup_date < today:
            logger.info("🔄 Kaçırılan temizlik tespit edildi, çalıştırılıyor...")
            asyncio.create_task(self.daily_cleanup())
            self.last_cleanup_date = today
    
    async def run(self):
        """Ana scheduler döngüsü"""
        logger.info("🚀 Cleanup scheduler başlatıldı")
        
        # İlk açılışta kaçırılan temizlikleri kontrol et
        self.check_missed_cleanup()
        
        # Günlük temizlik: Her gün 23:59
        schedule.every().day.at("23:59").do(
            lambda: asyncio.create_task(self.daily_cleanup())
        )
        
        # Aylık temizlik: Her 28 günde bir 00:00
        schedule.every(28).days.at("00:00").do(
            lambda: asyncio.create_task(self.monthly_cleanup())
        )
        
        # Fiyat tracker'ı başlat (her 5 dakikada bir)
        tracker = PriceTracker()
        
        while True:
            try:
                # Scheduled job'ları çalıştır
                schedule.run_pending()
                
                # Fiyat takibi yap
                await tracker.track_all_signals()
                
                # Kaçırılan temizlikleri kontrol et
                self.check_missed_cleanup()
                
                await asyncio.sleep(60)  # 1 dakika bekle
                
            except Exception as e:
                logger.error(f"Scheduler hatası: {e}")
                await asyncio.sleep(60)

async def start_scheduler():
    """Scheduler'ı başlat"""
    scheduler = CleanupScheduler()
    await scheduler.run()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(start_scheduler())
