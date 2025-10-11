# backend/feature_store.py
# Simple feature extractor: here we mock features from the CMC quote.
# In production, you'd compute EMA/RSI/volatility etc. from OHLCV history.

def build_features_from_quote(quote_json):
    """
    CoinMarketCap quote'undan tüm zaman dilimlerini çıkarır
    Mevcut zaman dilimleri: 1h, 24h, 7d, 30d, 60d, 90d
    """
    try:
        data = quote_json["data"]
        # get first key
        sym = list(data.keys())[0]
        q = data[sym]["quote"]["USD"]
        features = {
            "price": q.get("price"),
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
        return {}