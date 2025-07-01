import asyncio
from telethon import TelegramClient
from telethon.tl.functions.channels import GetChannelsRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, Channel
from config.settings import API_ID, API_HASH, PHONE_NUMBER, BOT_TOKEN

async def list_all_channels():
    """List all channels the user/bot is a member of"""
    
    # Determine whether to use bot token or user authentication
    if BOT_TOKEN:
        print("Using bot token authentication")
        client = TelegramClient('bot_session', API_ID, API_HASH)
        await client.start(bot_token=BOT_TOKEN)
    else:
        print("Using user authentication")
        client = TelegramClient('user_session', API_ID, API_HASH)
        await client.start(phone=PHONE_NUMBER)
    
    try:
        print("Fetching dialogs...")
        result = await client(GetDialogsRequest(
            offset_date=None,
            offset_id=0,
            offset_peer=InputPeerEmpty(),
            limit=500,
            hash=0
        ))
        
        channels = []
        for dialog in result.dialogs:
            entity = dialog.entity
            if isinstance(entity, Channel):
                if entity.username:
                    url = f"https://t.me/{entity.username}"
                else:
                    url = "Private channel (no username)"
                
                channels.append({
                    'id': entity.id,
                    'title': entity.title,
                    'username': entity.username,
                    'url': url,
                    'participants_count': getattr(entity, 'participants_count', 'Unknown'),
                    'is_broadcast': entity.broadcast
                })
        
        # Print channel information
        print(f"\nFound {len(channels)} channels:\n")
        print("=" * 80)
        for i, channel in enumerate(channels, 1):
            print(f"{i}. {channel['title']}")
            print(f"   URL: {channel['url']}")
            print(f"   Username: {channel['username'] or 'None'}")
            print(f"   Members: {channel['participants_count']}")
            print(f"   Is broadcast channel: {channel['is_broadcast']}")
            print("-" * 80)
        
        # Print config format
        print("\nFor config/channels.py, use:")
        print("TELEGRAM_CHANNELS = [")
        for channel in channels:
            if channel['username']:
                print(f"    'https://t.me/{channel['username']}',")
        print("]")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(list_all_channels()) 