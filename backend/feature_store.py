# backend/feature_store.py
# Simple feature extractor: here we mock features from the CMC quote.
# In production, you'd compute EMA/RSI/volatility etc. from OHLCV history.
def build_features_from_quote(quote_json):
    # quote_json is CMC quote response for one symbol
    try:
        data = quote_json["data"]
        # get first key
        sym = list(data.keys())[0]
        q = data[sym]["quote"]["USD"]
        features = {
            "price": q.get("price"),
            "percent_change_1h": q.get("percent_change_1h"),
            "percent_change_24h": q.get("percent_change_24h"),
            "market_cap": q.get("market_cap"),
            "volume_24h": q.get("volume_24h")
        }
        return features
    except Exception:
        return {}