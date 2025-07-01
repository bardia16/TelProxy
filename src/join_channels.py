import asyncio
from telethon import TelegramClient
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from config.settings import API_ID, API_HASH, BOT_TOKEN
from config.channels import TELEGRAM_CHANNELS

async def join_all_channels():
    """Join all channels listed in config/channels.py using bot token"""
    if not BOT_TOKEN:
        print("Error: No BOT_TOKEN found in settings. Please add it to your .env file.")
        return
    
    # Create client with bot token
    bot = TelegramClient('bot_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)
    
    print(f"Bot logged in successfully")
    
    for channel_url in TELEGRAM_CHANNELS:
        try:
            print(f"Attempting to join {channel_url}...")
            
            # Handle different URL formats
            if 'joinchat' in channel_url or '+' in channel_url:
                # It's a private channel with invite link
                if 'joinchat/' in channel_url:
                    # Extract hash from joinchat URL
                    invite_hash = channel_url.split('joinchat/')[1]
                else:
                    # Extract hash from t.me/+ URL
                    invite_hash = channel_url.split('+')[1]
                
                await bot(ImportChatInviteRequest(invite_hash))
            else:
                # It's a public channel
                # Extract username from URL
                if '/' in channel_url:
                    username = channel_url.split('/')[-1]
                else:
                    username = channel_url
                
                entity = await bot.get_entity(username)
                await bot(JoinChannelRequest(entity))
            
            print(f"✅ Successfully joined {channel_url}")
            # Wait a bit to avoid rate limits
            await asyncio.sleep(2)
            
        except Exception as e:
            print(f"❌ Failed to join {channel_url}: {e}")
    
    await bot.disconnect()
    print("Finished joining channels")

if __name__ == "__main__":
    asyncio.run(join_all_channels()) 