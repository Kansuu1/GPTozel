#!/usr/bin/env python3
"""
Analiz sürecini test eden ve detaylı sonuç gösteren script
"""
import asyncio
import sys
import os
sys.path.insert(0, '/app/backend')

from cmc_client import CMCClient
from feature_store import build_features_from_quote
from model_stub import predict_signal_from_features
from data_sync import read_config
import aiohttp

async def test_analysis():
    print("\n" + "="*60)
    print("📊 MM TRADING BOT PRO - ANALİZ TEST")
    print("="*60 + "\n")
    
    cfg = read_config()
    api_key = cfg.get("cmc_api_key") or os.getenv("CMC_API_KEY")
    selected_coins = cfg.get("selected_coins", [])
    threshold = cfg.get("threshold", 75)
    
    if not api_key:
        print("❌ API Key bulunamadı!")
        return
    
    print(f"🎯 Threshold: {threshold}%")
    print(f"🪙 Seçili Coinler: {', '.join(selected_coins)}")
    print(f"🔑 API Key uzunluğu: {len(api_key)} karakter")
    print("\n" + "-"*60 + "\n")
    
    async with aiohttp.ClientSession() as session:
        cmc = CMCClient(api_key)
        
        for coin in selected_coins[:5]:  # İlk 5 coin
            try:
                print(f"🔍 {coin} analiz ediliyor...")
                
                # Veri çekme
                quote = await cmc.get_quote(session, coin)
                features = build_features_from_quote(quote)
                
                # Fiyat bilgileri
                price = features.get('price', 0)
                change_1h = features.get('percent_change_1h', 0)
                change_24h = features.get('percent_change_24h', 0)
                
                print(f"   💰 Fiyat: ${price:,.2f}")
                print(f"   📈 1h Değişim: {change_1h:+.2f}%")
                print(f"   📊 24h Değişim: {change_24h:+.2f}%")
                
                # Sinyal üretimi
                timeframe = cfg.get("timeframe", "24h")
                signal_type, probability, tp, sl, weight_desc = predict_signal_from_features(features, timeframe)
                
                print(f"   🎯 Skor: {probability:.2f}%")
                
                if signal_type and probability >= threshold:
                    print(f"   ✅ SİNYAL: {signal_type} (Güvenilirlik: {probability:.2f}%)")
                    if tp and sl:
                        if signal_type == "LONG":
                            profit = ((tp - price) / price) * 100
                            loss = ((price - sl) / price) * 100
                        else:
                            profit = ((price - tp) / price) * 100
                            loss = ((sl - price) / price) * 100
                        
                        print(f"   🎯 Take Profit: ${tp:,.4f} (+{profit:.2f}%)")
                        print(f"   🛡 Stop Loss: ${sl:,.4f} (-{loss:.2f}%)")
                        print(f"   ⚖️ Risk/Reward: 1:{(profit/loss):.1f}")
                    print(f"   📱 Telegram bildirimi gönderilecek!")
                else:
                    if probability < threshold:
                        print(f"   ❌ Threshold altında ({probability:.2f}% < {threshold}%)")
                    else:
                        print(f"   ⚠️  Sinyal yok (düşük volatilite)")
                
                print("")
                
            except Exception as e:
                print(f"   ❌ Hata: {e}\n")
    
    print("-"*60)
    print("\n✅ Analiz tamamlandı!\n")

if __name__ == "__main__":
    asyncio.run(test_analysis())
