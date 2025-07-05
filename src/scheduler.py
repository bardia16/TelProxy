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
        """Run a single cycle of proxy extraction and validation"""
        try:
            await self.telegram_client.start_session()
            
            messages = await self.channel_scraper.scrape_all_channels()
            
            if not messages:
                return
            
            # Step 2: Extract proxies from messages
            all_proxies = []
            
            for message in messages:
                # Get all href attributes from the message
                hrefs = []
                if hasattr(message, 'entities'):
                    for entity in message.entities:
                        if hasattr(entity, 'url'):
                            hrefs.append(entity.url)
                
                # Extract proxies from both hrefs and message text
                proxies = self.proxy_extractor.extract_all_proxies(
                    hrefs=hrefs,
                    text=message.text if hasattr(message, 'text') else ""
                )
                all_proxies.extend(proxies)
            
            if not all_proxies:
                return
            
            # Step 3: Remove duplicates
            original_count = len(all_proxies)
            all_proxies = self.proxy_extractor.remove_duplicates(all_proxies)
            duplicates_removed = original_count - len(all_proxies)
            
            # Step 5: Validate proxies
            validation_attempt = 0
            working_proxies = []
            retry_delay = 60  # Initial delay in seconds
            
            while not working_proxies and validation_attempt < 3:
                validation_attempt += 1
                
                try:
                    working_proxies = self.proxy_validator.validate_proxies(all_proxies)
                    
                    if working_proxies:
                        break
                    
                    if validation_attempt < 3:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Double the delay for next attempt
                except Exception as e:
                    if validation_attempt < 3:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
            
            if working_proxies:
                # Step 6: Save working proxies
                self.proxy_storage.save_proxies_to_database(working_proxies)
                self.proxy_storage.save_proxies_to_json(working_proxies)
                
                # Step 8: Post to Telegram if configured
                if OUTPUT_CHANNEL:
                    message_id = await self.proxy_storage.post_proxies_to_telegram(working_proxies, validator=self.proxy_validator)
                
                # Step 9: Clean up old proxies
                removed_count = self.proxy_storage.remove_outdated_proxies(days_old=7)
            
        except Exception as e:
            raise
        finally:
            await self.telegram_client.close_session()
            await asyncio.sleep(1)  # Small delay before next cycle
    
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