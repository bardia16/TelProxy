import asyncio
from telegram import Bot
from telegram.error import TelegramError
from config.settings import BOT_TOKEN

async def list_all_channels():
    """List all channels the bot is a member of"""
    
    if not BOT_TOKEN:
        print("Error: No BOT_TOKEN found in settings. Please add it to your .env file.")
        return
    
    # Create bot instance
    bot = Bot(token=BOT_TOKEN)
    
    try:
        print("Fetching bot information...")
        bot_info = await bot.get_me()
        print(f"Connected as: {bot_info.first_name} (@{bot_info.username})")
        
        print("\nNote: python-telegram-bot doesn't provide a direct way to list all channels.")
        print("You'll need to manually track which channels your bot is added to.")
        print("Alternatively, you can use the Telegram API's getChats method with a user account.")
        
        print("\nFor config/channels.py, use:")
        print("TELEGRAM_CHANNELS = [")
        print("    'https://t.me/channel1',")
        print("    'https://t.me/channel2',")
        print("    # Add more channels here")
        print("]")
        
    except TelegramError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(list_all_channels()) 