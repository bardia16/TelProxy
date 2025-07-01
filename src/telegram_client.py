from telethon import TelegramClient as TelethonClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
import asyncio
from config.settings import API_ID, API_HASH, PHONE_NUMBER, SESSION_NAME, RATE_LIMIT_DELAY, BOT_TOKEN
import os


class TelegramClient:
    
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.use_bot_token = bool(BOT_TOKEN)
    
    async def start_session(self):
        if self.client and self.is_connected:
            return
        
        try:
            if self.use_bot_token:
                # Use bot token authentication
                self.client = TelethonClient(SESSION_NAME, API_ID, API_HASH)
                await self.client.start(bot_token=BOT_TOKEN)
            else:
                # Use user authentication with API ID and hash
                self.client = TelethonClient(SESSION_NAME, API_ID, API_HASH)
                await self.client.start(phone=PHONE_NUMBER)
                
                if not await self.client.is_user_authorized():
                    verification_code = input('Enter the verification code sent to your phone: ')
                    await self.client.sign_in(PHONE_NUMBER, verification_code)
                    
                    try:
                        await self.client.sign_in(code=verification_code)
                    except SessionPasswordNeededError:
                        two_step_password = input('Enter your two-step verification password: ')
                        await self.client.sign_in(password=two_step_password)
            
            self.is_connected = True
            print("✅ Connected to Telegram")
            
        except FloodWaitError as e:
            wait_time = e.seconds
            print(f"⚠️ Flood wait error. Need to wait {wait_time} seconds")
            await asyncio.sleep(wait_time)
            await self.start_session()
            
        except Exception as e:
            print(f"❌ Error connecting to Telegram: {e}")
            self.is_connected = False
    
    async def close_session(self):
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
    
    async def get_channel_messages(self, channel_url, limit=100):
        if not self.client or not self.is_connected:
            await self.start_session()
        
        try:
            entity = await self.client.get_entity(channel_url)
            
            messages = []
            
            history = await self.client(GetHistoryRequest(
                peer=entity,
                limit=limit,
                offset_date=None,
                offset_id=0,
                max_id=0,
                min_id=0,
                add_offset=0,
                hash=0
            ))
            
            for message in history.messages:
                if message.message:
                    message_data = {
                        'id': message.id,
                        'channel_id': entity.id,
                        'channel_name': getattr(entity, 'title', getattr(entity, 'username', str(entity.id))),
                        'date': message.date.strftime('%Y-%m-%d %H:%M:%S'),
                        'text': message.message,
                        'combined_text': message.message
                    }
                    
                    # Check for any media caption
                    if hasattr(message, 'media') and message.media:
                        if hasattr(message.media, 'caption') and message.media.caption:
                            message_data['combined_text'] += ' ' + message.media.caption
                    
                    messages.append(message_data)
            
            return messages
            
        except Exception as e:
            print(f"❌ Error fetching messages from {channel_url}: {e}")
            return []
    
    async def send_message(self, channel, message_text):
        if not self.client or not self.is_connected:
            await self.start_session()
        
        try:
            entity = await self.client.get_entity(channel)
            message = await self.client.send_message(entity, message_text)
            return message.id
        except Exception as e:
            print(f"❌ Error sending message to {channel}: {e}")
            return None
    
    async def pin_message(self, channel, message_id):
        if not self.client or not self.is_connected:
            await self.start_session()
        
        try:
            entity = await self.client.get_entity(channel)
            await self.client.pin_message(entity, message_id)
            return True
        except Exception as e:
            print(f"❌ Error pinning message {message_id} in {channel}: {e}")
            return False
    
    async def get_channel_entity(self, channel_url):
        if not self.is_connected:
            raise RuntimeError("Client must be connected before accessing channels")
        
        try:
            entity = await self.client.get_entity(channel_url)
            return entity
        except Exception as e:
            print(f"Failed to get entity for {channel_url}: {e}")
            return None
    
    async def fetch_channel_messages(self, channel_entity, limit=100):
        if not self.is_connected:
            raise RuntimeError("Client must be connected before fetching messages")
        
        messages = []
        try:
            async for message in self.client.iter_messages(channel_entity, limit=limit):
                messages.append(message)
                await asyncio.sleep(RATE_LIMIT_DELAY)
            
        except FloodWaitError as e:
            print(f"Rate limited, waiting {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Error fetching messages: {e}")
        
        return messages
    
    def is_connected(self):
        return self.client and self.client.is_connected() and self.is_connected 