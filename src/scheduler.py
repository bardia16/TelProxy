import asyncio
import schedule
import time
from datetime import datetime, timezone
from src.telegram_client import TelegramClient
from src.channel_scraper import ChannelScraper
from src.proxy_extractor import ProxyExtractor
from src.proxy_validator import ProxyValidator
from src.proxy_storage import ProxyStorage
from config.settings import OUTPUT_CHANNEL, SCHEDULER_INTERVAL_HOURS


class ProxyScheduler:
    
    def __init__(self):
        self.telegram_client = TelegramClient()
        self.channel_scraper = ChannelScraper(self.telegram_client)
        self.proxy_extractor = ProxyExtractor()
        self.proxy_validator = ProxyValidator()
        self.proxy_storage = ProxyStorage(
            telegram_client=self.telegram_client,
            output_channel=OUTPUT_CHANNEL
        )
        self.is_running = False
    
    async def run_hourly_cycle(self):
        print(f"\n🚀 Starting hourly proxy cycle at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
        
        try:
            await self.telegram_client.start_session()
            
            print("📡 Scraping channels for proxy messages...")
            messages = await self.channel_scraper.scrape_all_channels()
            
            if not messages:
                print("ℹ️ No relevant messages found this cycle")
                return
            
            print("🔍 Extracting proxies from messages...")
            all_proxies = []
            for message in messages:
                proxies = self.proxy_extractor.extract_all_proxies(message['combined_text'])
                all_proxies.extend(proxies)
            
            if not all_proxies:
                print("ℹ️ No valid proxies found this cycle")
                return
            
            print(f"✅ Extracted {len(all_proxies)} total proxies")
            
            # Print detailed information about each found proxy
            print("\n📋 Found Proxies (Before Validation):")
            print("-" * 60)
            print(f"{'Type':<10} {'Server':<30} {'Port':<8} {'Secret/Auth':<20}")
            print("-" * 60)
            
            for i, proxy in enumerate(all_proxies, 1):
                auth_info = ""
                if proxy.proxy_type == 'mtproto' and proxy.secret:
                    auth_info = f"Secret: {proxy.secret[:8]}..." if len(proxy.secret) > 8 else f"Secret: {proxy.secret}"
                elif proxy.proxy_type == 'socks5' and proxy.username:
                    auth_info = f"User: {proxy.username}"
                
                print(f"{proxy.proxy_type:<10} {proxy.server:<30} {proxy.port:<8} {auth_info:<20}")
                
                # Print only first 20 proxies if there are too many
                if i >= 20 and len(all_proxies) > 20:
                    print(f"... and {len(all_proxies) - 20} more proxies")
                    break
            
            print("-" * 60)
            print("\n🔧 Validating proxy connectivity...")
            working_proxies = await self.proxy_validator.validate_all_proxies(all_proxies)
            
            if not working_proxies:
                print("⚠️ No working proxies found this cycle")
                return
            
            print("💾 Saving proxies to local storage...")
            self.proxy_storage.save_proxies_to_database(working_proxies)
            self.proxy_storage.save_proxies_to_json(working_proxies)
            
            if OUTPUT_CHANNEL:
                print("📤 Posting proxies to Telegram channel...")
                message_id = await self.proxy_storage.post_proxies_to_telegram(working_proxies)
                if message_id:
                    print(f"✅ Successfully posted to channel with message ID: {message_id}")
            else:
                print("ℹ️ No output channel configured, skipping Telegram posting")
            
            print("🧹 Cleaning up outdated proxies...")
            removed_count = self.proxy_storage.remove_outdated_proxies(days_old=7)
            
            stats = self.proxy_validator.get_validation_summary()
            posting_stats = self.proxy_storage.get_posting_stats()
            
            print(f"\n📊 Cycle Summary:")
            print(f"   • Messages processed: {len(messages)}")
            print(f"   • Proxies extracted: {len(all_proxies)}")
            print(f"   • Working proxies: {len(working_proxies)}")
            print(f"   • Success rate: {stats['success_rate']:.1f}%")
            print(f"   • Posted to Telegram: {'Yes' if OUTPUT_CHANNEL and message_id else 'No'}")
            print(f"   • Outdated removed: {removed_count}")
            
        except Exception as e:
            print(f"❌ Error in hourly cycle: {e}")
        
        finally:
            await self.telegram_client.close_session()
            print(f"🏁 Hourly cycle completed at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
    
    def schedule_hourly_runs(self):
        schedule.every(SCHEDULER_INTERVAL_HOURS).hours.do(
            lambda: asyncio.create_task(self.run_hourly_cycle())
        )
        
        print(f"⏰ Scheduled to run every {SCHEDULER_INTERVAL_HOURS} hour(s)")
        print("🎯 Running initial cycle now...")
        
        asyncio.create_task(self.run_hourly_cycle())
    
    async def start_scheduler(self):
        self.is_running = True
        self.schedule_hourly_runs()
        
        print("🔄 Scheduler started. Press Ctrl+C to stop.")
        
        try:
            while self.is_running:
                schedule.run_pending()
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped by user")
        finally:
            self.is_running = False
    
    def stop_scheduler(self):
        self.is_running = False
        schedule.clear()
        print("🛑 Scheduler stopped")
    
    async def run_single_cycle(self):
        print("🎯 Running single proxy extraction cycle...")
        await self.run_hourly_cycle()


async def main():
    scheduler = ProxyScheduler()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'once':
        await scheduler.run_single_cycle()
    else:
        await scheduler.start_scheduler()


if __name__ == "__main__":
    asyncio.run(main()) 