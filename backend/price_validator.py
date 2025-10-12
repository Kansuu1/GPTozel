# backend/price_validator.py
"""
Fiyat doğrulama modülü
CMC API'den gelen fiyatı alternatif kaynaklarla karşılaştırır
"""
import aiohttp
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


async def get_dexscreener_price(symbol: str, chain: str = "bsc") -> Optional[float]:
    """
    DexScreener API'den fiyat al (DEX'lerdeki gerçek fiyat)
    
    Args:
        symbol: Coin sembolü
        chain: Blockchain (bsc, ethereum, solana, vb.)
    
    Returns:
        Fiyat veya None
    """
    # Contract address mapping (BSC için)
    contracts = {
        "COAI": {
            "chain": "bsc",
            "address": "0x0A8D6C86e1bcE73fE4D0bD531e1a567306836EA5"
        }
    }
    
    contract_info = contracts.get(symbol.upper())
    if not contract_info:
        return None
    
    try:
        chain = contract_info["chain"]
        address = contract_info["address"]
        url = f"https://api.dexscreener.com/latest/dex/tokens/{address}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # En yüksek likiditeye sahip pair'i al
                    pairs = data.get("pairs", [])
                    if pairs:
                        # Likiditeye göre sırala
                        pairs_sorted = sorted(pairs, key=lambda x: float(x.get("liquidity", {}).get("usd", 0)), reverse=True)
                        
                        if pairs_sorted:
                            best_pair = pairs_sorted[0]
                            price = float(best_pair.get("priceUsd", 0))
                            dex_name = best_pair.get("dexId", "Unknown")
                            liquidity = best_pair.get("liquidity", {}).get("usd", 0)
                            
                            if price > 0:
                                logger.info(f"[{symbol}] DexScreener fiyatı: ${price} (DEX: {dex_name}, Liq: ${liquidity:,.0f})")
                                return price
                    
                    logger.warning(f"[{symbol}] DexScreener'da pair bulunamadı")
                    return None
                else:
                    logger.warning(f"[{symbol}] DexScreener API hatası: {response.status}")
                    return None
    
    except Exception as e:
        logger.error(f"[{symbol}] DexScreener fiyat alma hatası: {e}")
        return None


async def get_binance_price(symbol: str) -> Optional[float]:
    """
    Binance API'den fiyat al (en gerçek zamanlı)
    
    Args:
        symbol: Coin sembolü (BTC, ETH, vb.)
    
    Returns:
        Fiyat veya None
    """
    # Binance pair mapping
    pairs = {
        "BTC": "BTCUSDT",
        "ETH": "ETHUSDT",
        "BNB": "BNBUSDT",
        "SOL": "SOLUSDT",
        "ADA": "ADAUSDT",
        "XRP": "XRPUSDT",
        "DOGE": "DOGEUSDT",
        "AVAX": "AVAXUSDT",
        "MATIC": "MATICUSDT",
        "DOT": "DOTUSDT",
        "LINK": "LINKUSDT",
        "UNI": "UNIUSDT",
        "COAI": "COAIUSDT"  # Binance'de varsa
    }
    
    pair = pairs.get(symbol.upper())
    if not pair:
        return None
    
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    data = await response.json()
                    price = data.get("price")
                    if price:
                        price = float(price)
                        logger.info(f"[{symbol}] Binance fiyatı: ${price}")
                        return price
                else:
                    logger.debug(f"[{symbol}] Binance'de pair bulunamadı: {pair}")
                    return None
    
    except Exception as e:
        logger.debug(f"[{symbol}] Binance fiyat alma hatası: {e}")
        return None


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
    CMC fiyatını doğrula (DexScreener, Binance ve CoinGecko ile)
    
    Args:
        symbol: Coin sembolü
        cmc_price: CMC'den gelen fiyat
        tolerance: Kabul edilebilir fark yüzdesi (varsayılan %15)
    
    Returns:
        {
            "is_valid": bool,
            "cmc_price": float,
            "dex_price": float,
            "binance_price": float,
            "coingecko_price": float,
            "diff_percent": float,
            "warning": str,
            "recommended_price": float
        }
    """
    result = {
        "is_valid": True,
        "cmc_price": cmc_price,
        "dex_price": None,
        "binance_price": None,
        "coingecko_price": None,
        "diff_percent": 0,
        "warning": None,
        "recommended_price": cmc_price
    }
    
    # ÖNCELİK 1: DexScreener (DEX'lerdeki gerçek fiyat)
    dex_price = await get_dexscreener_price(symbol)
    result["dex_price"] = dex_price
    
    # ÖNCELİK 2: Binance
    binance_price = await get_binance_price(symbol)
    result["binance_price"] = binance_price
    
    # ÖNCELİK 3: CoinGecko
    cg_price = await get_coingecko_price(symbol)
    result["coingecko_price"] = cg_price
    
    # Hangi fiyatı referans alacağımıza karar ver (öncelik sırasına göre)
    reference_price = None
    reference_source = None
    
    if dex_price:
        reference_price = dex_price
        reference_source = "DexScreener"
    elif binance_price:
        reference_price = binance_price
        reference_source = "Binance"
    elif cg_price:
        reference_price = cg_price
        reference_source = "CoinGecko"
    else:
        # Hiçbir alternatif yoksa CMC'ye güven
        result["warning"] = "⚠️ Alternatif fiyat kaynağı bulunamadı, CMC fiyatı kullanılıyor"
        logger.warning(f"[{symbol}] {result['warning']}")
        return result
    
    # Fark yüzdesini hesapla
    diff_percent = abs((cmc_price - reference_price) / reference_price) * 100
    result["diff_percent"] = round(diff_percent, 2)
    
    # Tolerans kontrolü
    if diff_percent > tolerance * 100:
        result["is_valid"] = False
        result["recommended_price"] = reference_price
        result["warning"] = f"⚠️ Fiyat farkı yüksek! CMC: ${cmc_price:.2f}, {reference_source}: ${reference_price:.2f} (Fark: %{diff_percent:.1f})"
        logger.warning(f"[{symbol}] {result['warning']}")
    else:
        logger.info(f"[{symbol}] Fiyat doğrulandı - CMC: ${cmc_price:.2f}, {reference_source}: ${reference_price:.2f} (Fark: %{diff_percent:.1f})")
    
    return result


async def get_validated_price(symbol: str, cmc_price: float) -> float:
    """
    Doğrulanmış fiyat döndür
    Eğer CMC ile alternatif kaynaklar arasında büyük fark varsa, en güvenilir kaynağı kullan
    
    Öncelik: Binance > CoinGecko > CMC
    
    Args:
        symbol: Coin sembolü
        cmc_price: CMC'den gelen fiyat
    
    Returns:
        Doğrulanmış fiyat
    """
    validation = await validate_price(symbol, cmc_price)
    
    if not validation["is_valid"]:
        # CMC fiyatı güvenilir değil, alternatifi kullan
        recommended = validation["recommended_price"]
        source = "Binance" if validation["binance_price"] else "CoinGecko"
        logger.warning(f"[{symbol}] ⚠️ CMC fiyatı yerine {source} fiyatı kullanılıyor: ${recommended:.2f}")
        return recommended
    
    # CMC fiyatı güvenilir
    return cmc_price
