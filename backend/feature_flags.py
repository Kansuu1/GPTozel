# backend/feature_flags.py
"""
Feature Flags
Yeni özellikleri kontrollü şekilde açmak için
"""
import os
import logging

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Feature flag yönetimi"""
    
    # Feature flag'ler
    ENABLE_CANDLE_INTERVAL_ANALYSIS = "enable_candle_interval_analysis"
    
    # Default değerler
    DEFAULTS = {
        ENABLE_CANDLE_INTERVAL_ANALYSIS: False,
    }
    
    @staticmethod
    def is_enabled(flag_name: str) -> bool:
        """
        Feature flag aktif mi kontrol et
        
        Args:
            flag_name: Flag adı
        
        Returns:
            True/False
        """
        # Environment variable'dan oku
        env_var = f"FEATURE_{flag_name.upper()}"
        env_value = os.environ.get(env_var)
        
        if env_value is not None:
            # Environment variable varsa onu kullan
            return env_value.lower() in ('true', '1', 'yes', 'on')
        
        # Default değer
        default_value = FeatureFlags.DEFAULTS.get(flag_name, False)
        return default_value
    
    @staticmethod
    def enable_candle_interval_analysis() -> bool:
        """Candle interval bazlı analiz aktif mi?"""
        enabled = FeatureFlags.is_enabled(FeatureFlags.ENABLE_CANDLE_INTERVAL_ANALYSIS)
        if enabled:
            logger.info("🔧 Feature Flag: Candle Interval Analysis ENABLED")
        return enabled
    
    @staticmethod
    def set_flag(flag_name: str, value: bool):
        """
        Feature flag değerini değiştir (runtime)
        
        Args:
            flag_name: Flag adı
            value: True/False
        """
        env_var = f"FEATURE_{flag_name.upper()}"
        os.environ[env_var] = str(value).lower()
        logger.info(f"🏁 Feature Flag Updated: {flag_name} = {value}")


# Global instance
feature_flags = FeatureFlags()
