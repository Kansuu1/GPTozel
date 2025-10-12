# backend/price_validator.py
"""
Fiyat doğrulama modülü
CMC API'den gelen fiyatı alternatif kaynaklarla karşılaştırır
"""
import aiohttp
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


async def get_coingecko_price(symbol: str) -> Optional[float]:
    """
    CoinGecko API'den fiyat al
    
    Args:
        symbol: Coin sembolü (BTC, ETH, vb.)
    
    Returns:
        Fiyat veya None
    """
    # Symbol'den CoinGecko ID'ye mapping
    symbol_to_id = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "BNB": "binancecoin",
        "SOL": "solana",
        "ADA": "cardano",
        "XRP": "ripple",
        "DOGE": "dogecoin",
        "AVAX": "avalanche-2",
        "MATIC": "matic-network",
        "DOT": "polkadot",
        "LINK": "chainlink",
        "UNI": "uniswap",
        "COAI": "chainopera-ai"
    }
    
    coin_id = symbol_to_id.get(symbol.upper())
    if not coin_id:
        logger.warning(f"[{symbol}] CoinGecko ID bulunamadı")
        return None
    
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data.get(coin_id, {}).get("usd")
                    if price:
                        logger.info(f"[{symbol}] CoinGecko fiyatı: ${price}")
                        return float(price)
                else:
                    logger.warning(f"[{symbol}] CoinGecko API hatası: {response.status}")
                    return None
    
    except Exception as e:
        logger.error(f"[{symbol}] CoinGecko fiyat alma hatası: {e}")
        return None


async def validate_price(symbol: str, cmc_price: float, tolerance: float = 0.15) -> Dict:
    """
    CMC fiyatını doğrula
    
    Args:
        symbol: Coin sembolü
        cmc_price: CMC'den gelen fiyat
        tolerance: Kabul edilebilir fark yüzdesi (varsayılan %15)
    
    Returns:
        {
            "is_valid": bool,
            "cmc_price": float,
            "coingecko_price": float,
            "diff_percent": float,
            "warning": str
        }
    """
    result = {
        "is_valid": True,
        "cmc_price": cmc_price,
        "coingecko_price": None,
        "diff_percent": 0,
        "warning": None
    }
    
    # CoinGecko'dan fiyat al
    cg_price = await get_coingecko_price(symbol)
    
    if cg_price is None:
        # CoinGecko'dan fiyat alınamadı, CMC'ye güven
        result["warning"] = "CoinGecko fiyatı alınamadı, CMC fiyatı kullanılıyor"
        return result
    
    result["coingecko_price"] = cg_price
    
    # Fark yüzdesini hesapla
    diff_percent = abs((cmc_price - cg_price) / cg_price) * 100
    result["diff_percent"] = round(diff_percent, 2)
    
    # Tolerans kontrolü
    if diff_percent > tolerance * 100:
        result["is_valid"] = False
        result["warning"] = f"⚠️ Fiyat farkı çok yüksek! CMC: ${cmc_price:.2f}, CoinGecko: ${cg_price:.2f} (Fark: %{diff_percent:.1f})"
        logger.warning(f"[{symbol}] {result['warning']}")
    else:
        logger.info(f"[{symbol}] Fiyat doğrulandı - CMC: ${cmc_price:.2f}, CG: ${cg_price:.2f} (Fark: %{diff_percent:.1f})")
    
    return result


async def get_validated_price(symbol: str, cmc_price: float) -> float:
    """
    Doğrulanmış fiyat döndür
    Eğer CMC ile CoinGecko arasında büyük fark varsa, CoinGecko'yu kullan
    
    Args:
        symbol: Coin sembolü
        cmc_price: CMC'den gelen fiyat
    
    Returns:
        Doğrulanmış fiyat
    """
    validation = await validate_price(symbol, cmc_price)
    
    if not validation["is_valid"] and validation["coingecko_price"]:
        # CMC fiyatı güvenilir değil, CoinGecko'yu kullan
        logger.warning(f"[{symbol}] CMC fiyatı yerine CoinGecko fiyatı kullanılıyor: ${validation['coingecko_price']}")
        return validation["coingecko_price"]
    
    # CMC fiyatı güvenilir
    return cmc_price
