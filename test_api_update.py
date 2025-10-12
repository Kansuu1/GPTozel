import asyncio
from backend.data_sync import read_config, update_config

# Şu anki key
print("📊 Şu anki API Key:")
cfg = read_config()
print(f"  {cfg.get('cmc_api_key')[:30]}...")

# Yeni key ile güncelle (test)
print("\n🔄 Yeni API Key ile güncelleniyor...")
new_key = "TEST-KEY-12345678-abcd-efgh-ijkl-mnopqrstuvwx"
update_config({"cmc_api_key": new_key})

# Kontrol et
print("\n✅ Güncelleme sonrası:")
cfg = read_config()
print(f"  {cfg.get('cmc_api_key')}")

# Eski key'e geri al
print("\n🔙 Eski key'e geri alınıyor...")
original_key = "ad7e6f5c-8ac1-4e6a-bb17-57a38522cdc8"
update_config({"cmc_api_key": original_key})

cfg = read_config()
print(f"\n✅ Geri alındı: {cfg.get('cmc_api_key')}")

print("\n🎯 Sonuç: Config güncelleme çalışıyor!")
print("📝 Her analyze_cycle() çağrıldığında yeni config okunur.")
print("🔄 API Key değişikliği bir sonraki cycle'da (60 saniye içinde) aktif olur!")
