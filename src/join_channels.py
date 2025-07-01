import asyncio
import re
from telegram import Bot
from telegram.error import TelegramError
from config.settings import BOT_TOKEN
from config.channels import TELEGRAM_CHANNELS

async def join_all_channels():
    """Join all channels listed in config/channels.py using bot token"""
    if not BOT_TOKEN:
        print("Error: No BOT_TOKEN found in settings. Please add it to your .env file.")
        return
    
    # Create bot instance
    bot = Bot(token=BOT_TOKEN)
    
    print(f"Bot logged in successfully")
    
    # Note: python-telegram-bot doesn't have direct methods to join channels
    # We can only check if the bot is already in the channel by trying to get chat info
    
    for channel_url in TELEGRAM_CHANNELS:
        try:
            print(f"Checking access to {channel_url}...")
            
            # Extract channel username or ID from URL
            channel_id = extract_channel_id(channel_url)
            
            if not channel_id:
                print(f"❌ Could not extract channel ID from {channel_url}")
                continue
            
            # Try to get chat info to check if bot has access
            chat = await bot.get_chat(channel_id)
            
            print(f"✅ Bot has access to {chat.title} ({chat.username or chat.id})")
            
            # Wait a bit to avoid rate limits
            await asyncio.sleep(2)
            
        except TelegramError as e:
            print(f"❌ Bot doesn't have access to {channel_url}: {e}")
            print("Note: To join private channels with python-telegram-bot, you need to:")
            print("1. Generate an invite link for the channel")
            print("2. Open the link manually and add the bot as an administrator")
    
    print("Finished checking channel access")

def extract_channel_id(channel_url):
    """Extract channel username or ID from various URL formats"""
    # Handle t.me links
    if 't.me/' in channel_url:
        # Public channel
        if 'joinchat' not in channel_url and '+' not in channel_url:
            return '@' + channel_url.split('t.me/')[-1].split('/')[0]
        # We can't extract IDs from private channel links
        else:
            return None
    
    # Handle @username format
    elif channel_url.startswith('@'):
        return channel_url
    
    # Handle plain username
    else:
        return '@' + channel_url

if __name__ == "__main__":
    asyncio.run(join_all_channels()) 