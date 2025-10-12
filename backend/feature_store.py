# backend/feature_store.py
# Simple feature extractor: here we mock features from the CMC quote.
# In production, you'd compute EMA/RSI/volatility etc. from OHLCV history.

import asyncio
import logging

logger = logging.getLogger(__name__)


def build_features_from_quote(quote_json, validated_price=None):
    """
    CoinMarketCap quote'undan tüm zaman dilimlerini çıkarır
    Mevcut zaman dilimleri: 1h, 24h, 7d, 30d, 60d, 90d
    
    Args:
        quote_json: CMC API response
        validated_price: Doğrulanmış fiyat (opsiyonel)
    """
    try:
        data = quote_json["data"]
        # get first key
        sym = list(data.keys())[0]
        q = data[sym]["quote"]["USD"]
        
        # CMC fiyatını al
        cmc_price = q.get("price")
        
        # Eğer doğrulanmış fiyat varsa onu kullan
        final_price = validated_price if validated_price is not None else cmc_price
        
        if validated_price and validated_price != cmc_price:
            logger.info(f"[{sym}] Fiyat override: CMC ${cmc_price:.2f} → Validated ${validated_price:.2f}")
        
        features = {
            "price": final_price,
            "cmc_price": cmc_price,  # Orijinal CMC fiyatını da sakla
            "percent_change_1h": q.get("percent_change_1h"),
            "percent_change_24h": q.get("percent_change_24h"),
            "percent_change_7d": q.get("percent_change_7d"),
            "percent_change_30d": q.get("percent_change_30d"),
            "percent_change_60d": q.get("percent_change_60d"),
            "percent_change_90d": q.get("percent_change_90d"),
            "market_cap": q.get("market_cap"),
            "volume_24h": q.get("volume_24h"),
            "volume_change_24h": q.get("volume_change_24h")
        }
        return features
    except Exception as e:
        logger.error(f"Feature extraction hatası: {e}")
        return {}