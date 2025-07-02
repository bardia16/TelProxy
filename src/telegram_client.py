import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from telethon import TelegramClient as TelethonClient, connection
from telethon.sessions import StringSession
from telethon.tl.types import Message, Channel
from telethon.errors import SessionPasswordNeededError
from config.settings import (
    API_ID, API_HASH, PHONE_NUMBER, SESSION_NAME,
    CHANNEL_MESSAGE_LIMIT, INITIAL_PROXY
)


class TelegramClient:
    def __init__(self):
        self.is_connected = False
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Telethon client with MTProto proxy"""
        try:
            # Configure MTProto proxy
            if INITIAL_PROXY and INITIAL_PROXY['type'] == 'mtproto':
                proxy = (
                    INITIAL_PROXY['server'],
                    int(INITIAL_PROXY['port']),
                    INITIAL_PROXY['secret']
                )
                connection_type = connection.ConnectionTcpMTProxyRandomizedIntermediate
                print(f"🔗 Configuring Telethon with MTProto proxy: {INITIAL_PROXY['server']}:{INITIAL_PROXY['port']}")
            else:
                proxy = None
                connection_type = None
                print("⚠️ No MTProto proxy configured, using direct connection")
            
            # Initialize Telethon client
            self.client = TelethonClient(
                StringSession(),  # Use string session for better portability
                API_ID,
                API_HASH,
                connection=connection_type,
                proxy=proxy,
                device_model='Desktop',
                system_version='Windows 10',
                app_version='1.0',
                lang_code='en'
            )
            
        except Exception as e:
            print(f"❌ Error initializing Telethon client: {e}")
            self.client = None
    
    async def start_session(self):
        """Start the Telethon session with phone number authentication"""
        if self.is_connected:
            return
        
        if not self.client:
            print("❌ Telethon client not initialized")
            return
        
        try:
            print("📱 Starting Telethon session...")
            
            # Start the client and connect
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                print(f"📞 Sending code to {PHONE_NUMBER}...")
                await self.client.send_code_request(PHONE_NUMBER)
                
                code = input("Enter the code you received: ")
                try:
                    await self.client.sign_in(PHONE_NUMBER, code)
                except SessionPasswordNeededError:
                    # 2FA is enabled
                    password = input("Enter your 2FA password: ")
                    await self.client.sign_in(password=password)
            
            # Get account info
            me = await self.client.get_me()
            self.is_connected = True
            print(f"✅ Connected to Telegram as: {me.first_name} (@{me.username})")
            
        except Exception as e:
            print(f"❌ Error connecting to Telegram: {e}")
            self.is_connected = False
    
    async def close_session(self):
        """Close the Telethon session"""
        if self.client:
            await self.client.disconnect()
        self.is_connected = False
    
    def set_proxy_storage(self, proxy_storage):
        """Maintained for compatibility with scheduler"""
        pass
    
    async def get_channel_messages(self, channel_url: str, limit: int = CHANNEL_MESSAGE_LIMIT) -> List[Dict[str, Any]]:
        """Get messages from a Telegram channel using Telethon"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Clean up the channel URL to get the username
            if '@' in channel_url:
                channel_name = channel_url.replace('@', '')
            elif 't.me/' in channel_url:
                channel_name = channel_url.split('t.me/')[1]
            else:
                channel_name = channel_url
            
            # Get the channel entity
            channel = await self.client.get_entity(channel_name)
            
            if not isinstance(channel, Channel):
                print(f"❌ {channel_name} is not a channel")
                return []
            
            # Get messages
            messages = []
            async for message in self.client.iter_messages(channel, limit=limit):
                if not isinstance(message, Message):
                    continue
                
                # Create message data structure
                message_data = {
                    'id': message.id,
                    'text': message.text,
                    'date': message.date,
                    'channel_id': channel.id,
                    'channel_name': channel_name,
                }
                
                messages.append(message_data)
            
            return messages
            
        except Exception as e:
            print(f"❌ Error getting channel messages: {e}")
            return []
    
    async def send_message(self, channel: str, message_text: str) -> Optional[int]:
        """Send a message to a Telegram channel"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Get the channel entity
            channel_entity = await self.client.get_entity(channel)
            
            # Send the message
            message = await self.client.send_message(
                channel_entity,
                message_text,
                parse_mode='md'
            )
            return message.id
            
        except Exception as e:
            print(f"❌ Error sending message to {channel}: {e}")
            return None
    
    async def edit_message(self, channel: str, message_id: int, new_text: str) -> bool:
        """Edit an existing message in a Telegram channel"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Get the channel entity
            channel_entity = await self.client.get_entity(channel)
            
            # Edit the message
            await self.client.edit_message(
                channel_entity,
                message_id,
                new_text,
                parse_mode='md'
            )
            return True
            
        except Exception as e:
            print(f"❌ Error editing message {message_id} in {channel}: {e}")
            return False
    
    async def get_pinned_messages(self, channel: str) -> List[int]:
        """Get pinned messages from a Telegram channel"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Get the channel entity
            channel_entity = await self.client.get_entity(channel)
            
            # Get the discussion message
            messages = await self.client.get_messages(
                channel_entity,
                filter=lambda m: m.pinned
            )
            return [msg.id for msg in messages if msg.pinned]
            
        except Exception as e:
            print(f"❌ Error getting pinned messages from {channel}: {e}")
            return []
    
    async def pin_message(self, channel: str, message_id: int) -> bool:
        """Pin a message in a Telegram channel"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Get the channel entity
            channel_entity = await self.client.get_entity(channel)
            
            # Pin the message
            await self.client.pin_message(
                channel_entity,
                message_id,
                notify=False
            )
            return True
            
        except Exception as e:
            print(f"❌ Error pinning message {message_id} in {channel}: {e}")
            return False
    
    async def get_channel_entity(self, channel_url):
        """
        Get basic channel info using web scraping
        """
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Clean up the channel URL
            if '@' in channel_url:
                channel_name = channel_url.replace('@', '')
            elif 't.me/' in channel_url:
                channel_name = channel_url.split('t.me/')[1]
            else:
                channel_name = channel_url
            
            # Create a simple entity-like object
            entity = {
                'id': channel_name,  # Using name as ID
                'username': channel_name,
                'title': channel_name
            }
            
            return entity
        except Exception as e:
            print(f"Failed to get entity for {channel_url}: {e}")
            return None
    
    async def fetch_channel_messages(self, channel_entity, limit=CHANNEL_MESSAGE_LIMIT):
        """
        Fetch messages from a channel using web scraping
        """
        if not self.is_connected:
            await self.start_session()
        
        try:
            channel_name = channel_entity.get('username', channel_entity.get('id'))
            
            # Get messages using the get_channel_messages method
            message_data = await self.get_channel_messages(channel_name, limit=limit)
            
            # Convert to a format similar to what the old method returned
            messages = []
            for msg in message_data:
                message = type('Message', (), {})
                message.id = msg['id']
                message.date = datetime.strptime(msg['date'], '%Y-%m-%d %H:%M:%S')
                message.message = msg['text']
                message.html = msg['html']
                message.hrefs = msg['hrefs']
                
                # Add chat attribute
                message.chat = type('Chat', (), {})
                message.chat.username = msg['channel_name']
                
                # Add entities attribute (empty list for now)
                message.entities = []
                
                messages.append(message)
            
            return messages
            
        except Exception as e:
            print(f"Error fetching messages: {e}")
            return [] 