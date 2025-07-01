from telethon import TelegramClient as TelethonClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.types import PeerChannel
import asyncio
from config.settings import API_ID, API_HASH, PHONE_NUMBER, SESSION_NAME, RATE_LIMIT_DELAY


class TelegramClient:
    
    def __init__(self):
        self.client = None
        self.is_authenticated = False
    
    async def initialize_connection(self):
        if not API_ID or not API_HASH:
            raise ValueError("API_ID and API_HASH must be configured in settings")
        
        self.client = TelethonClient(SESSION_NAME, API_ID, API_HASH)
        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            self.is_authenticated = False
        else:
            self.is_authenticated = True
    
    async def authenticate_user(self):
        if not self.client:
            await self.initialize_connection()
        
        if not await self.client.is_user_authorized():
            if not PHONE_NUMBER:
                raise ValueError("PHONE_NUMBER must be configured for authentication")
            
            await self.client.send_code_request(PHONE_NUMBER)
            code = input('Enter the verification code: ')
            
            try:
                await self.client.sign_in(PHONE_NUMBER, code)
            except SessionPasswordNeededError:
                password = input('Enter your 2FA password: ')
                await self.client.sign_in(password=password)
            
            self.is_authenticated = True
    
    async def start_session(self):
        await self.initialize_connection()
        if not self.is_authenticated:
            await self.authenticate_user()
        await self.client.start()
    
    async def close_session(self):
        if self.client and self.client.is_connected():
            await self.client.disconnect()
        self.is_authenticated = False
    
    async def get_channel_entity(self, channel_url):
        if not self.is_authenticated:
            raise RuntimeError("Client must be authenticated before accessing channels")
        
        try:
            entity = await self.client.get_entity(channel_url)
            return entity
        except Exception as e:
            print(f"Failed to get entity for {channel_url}: {e}")
            return None
    
    async def fetch_channel_messages(self, channel_entity, limit=100):
        if not self.is_authenticated:
            raise RuntimeError("Client must be authenticated before fetching messages")
        
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
        return self.client and self.client.is_connected() and self.is_authenticated 