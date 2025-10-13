# backend/cmc_client.py
import time, asyncio, aiohttp
from aiolimiter import AsyncLimiter
from typing import Dict
import os

# Free tier typical limit: 30 req / min (configure via env if needed)
CMC_RATE_LIMIT = 30
limiter = AsyncLimiter(CMC_RATE_LIMIT, 60)

class CMCClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base = "https://pro-api.coinmarketcap.com"
        self._cache: Dict = {}

    async def _request(self, session: aiohttp.ClientSession, path: str, params=None):
        async with limiter:
            url = f"{self.base}{path}"
            headers = {"X-CMC_PRO_API_KEY": self.api_key}
            try:
                async with session.get(url, headers=headers, params=params, timeout=20) as resp:
                    resp.raise_for_status()
                    return await resp.json()
            except Exception as e:
                # simple retry strategy
                await asyncio.sleep(1)
                async with session.get(url, headers=headers, params=params, timeout=20) as resp:
                    resp.raise_for_status()
                    return await resp.json()

    async def get_quote(self, session: aiohttp.ClientSession, symbol: str):
        # simple short cache (10s)
        key = ("quote", symbol)
        now = time.time()
        if key in self._cache and now - self._cache[key][0] < 10:
            return self._cache[key][1]
        data = await self._request(session, "/v1/cryptocurrency/quotes/latest", params={"symbol": symbol, "convert":"USD"})
        self._cache[key] = (now, data)
        return data

    async def get_listings(self, session: aiohttp.ClientSession, limit=200):
        key = ("listings", limit)
        now = time.time()
        if key in self._cache and now - self._cache[key][0] < 60:
            return self._cache[key][1]
        data = await self._request(session, "/v1/cryptocurrency/listings/latest", params={"limit": limit})
        self._cache[key] = (now, data)
        return data

    async def get_historical_quotes(self, session: aiohttp.ClientSession, symbol: str, time_start: str, time_end: str, interval: str = "1h"):
        """
        Geçmiş fiyat verilerini çek
        
        Args:
            symbol: Coin sembolü (BTC, ETH, vb.)
            time_start: Başlangıç tarihi (ISO format: 2025-01-01T00:00:00Z)
            time_end: Bitiş tarihi (ISO format)
            interval: '5m', '10m', '15m', '30m', '1h', '2h', '6h', '12h', '24h', '1d', '7d', '14d', '30d'
        
        Returns:
            Historical quotes data
        """
        params = {
            "symbol": symbol,
            "time_start": time_start,
            "time_end": time_end,
            "interval": interval,
            "convert": "USD"
        }
        
        data = await self._request(session, "/v2/cryptocurrency/quotes/historical", params=params)
        return data