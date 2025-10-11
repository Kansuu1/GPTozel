import asyncio
from backend.analyzer import analyze_cycle

async def main():
    print("🚀 Manuel analiz başlatılıyor...")
    await analyze_cycle()
    print("✅ Analiz tamamlandı!")

if __name__ == "__main__":
    asyncio.run(main())
