import asyncio
import sys
from src.scheduler import ProxyScheduler


async def main():
    print("🔍 Telegram Proxy Scraper")
    print("========================")
    
    scheduler = ProxyScheduler()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'once':
            print("🎯 Running single extraction cycle...")
            await scheduler.run_single_cycle()
        elif sys.argv[1] == 'schedule':
            print("⏰ Starting scheduled hourly runs...")
            await scheduler.start_scheduler()
        else:
            print("Usage:")
            print("  python -m src.main once      # Run single cycle")
            print("  python -m src.main schedule  # Start hourly scheduler")
            print("  python -m src.main           # Run single cycle (default)")
    else:
        print("🎯 Running single extraction cycle...")
        await scheduler.run_single_cycle()


if __name__ == "__main__":
    asyncio.run(main()) 