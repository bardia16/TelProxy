import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from telethon import TelegramClient as TelethonClient
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Message
from telethon.tl.functions.channels import JoinChannelRequest
from config.settings import (
    API_ID, API_HASH, PHONE_NUMBER, BOT_TOKEN,
    CHANNEL_MESSAGE_LIMIT, INITIAL_PROXY
)
import config.settings
from src.proxy_extractor import ProxyData


class TelegramClient:
    def __init__(self):
        self.is_connected = False
        self.client = None
        self.proxy_storage = None
        self._init_client()
    
    def _init_client(self):
        """Initialize Telethon client with MTProto proxy"""
        try:
            # Get proxy configuration
            proxy = self._get_initial_proxy()
            
            # Configure client with proxy if available
            if proxy and proxy.proxy_type == 'mtproto':
                print(f"🔗 Configuring Telethon with MTProto proxy: {proxy.server}:{proxy.port}")
                self.client = TelethonClient(
                    StringSession(),
                    API_ID,
                    API_HASH,
                    proxy=(
                        'mtproto',
                        proxy.server,
                        int(proxy.port),
                        proxy.secret
                    ) if proxy.secret else None
                )
            else:
                print("ℹ️ Initializing Telethon without proxy")
                self.client = TelethonClient(
                    StringSession(),
                    API_ID,
                    API_HASH
                )
            
        except Exception as e:
            print(f"❌ Error initializing Telethon client: {e}")
            # Initialize without proxy as fallback
            self.client = TelethonClient(
                StringSession(),
                API_ID,
                API_HASH
            )
    
    def _get_initial_proxy(self) -> Optional[ProxyData]:
        """Get the initial proxy from settings if configured"""
        if not INITIAL_PROXY or not INITIAL_PROXY['server'] or not INITIAL_PROXY['port']:
            return None
        
        try:
            proxy = ProxyData(
                proxy_type=INITIAL_PROXY['type'],
                server=INITIAL_PROXY['server'],
                port=INITIAL_PROXY['port'],
                secret=INITIAL_PROXY.get('secret'),
                username=INITIAL_PROXY.get('username'),
                password=INITIAL_PROXY.get('password')
            )
            print(f"🔗 Using initial {proxy.proxy_type} proxy: {proxy.server}:{proxy.port}")
            return proxy
        except Exception as e:
            print(f"❌ Error configuring initial proxy: {e}")
            return None
    
    def set_proxy_storage(self, proxy_storage):
        """Set the proxy storage instance"""
        self.proxy_storage = proxy_storage
    
    async def start_session(self):
        """Start the Telethon client session"""
        if self.is_connected:
            return
        
        try:
            # Start the client
            await self.client.start(phone=PHONE_NUMBER)
            self.is_connected = True
            me = await self.client.get_me()
            print(f"✅ Connected to Telegram as: {me.first_name}")
            
        except Exception as e:
            print(f"❌ Error connecting to Telegram: {e}")
            self.is_connected = False
    
    async def close_session(self):
        """Close the Telethon client session"""
        if self.client:
            await self.client.disconnect()
        self.is_connected = False
    
    async def get_channel_entity(self, channel_url: str) -> Optional[Channel]:
        """Get a channel entity from its URL or username"""
        try:
            # Clean up the channel URL/username
            if '@' in channel_url:
                channel_name = channel_url.replace('@', '')
            elif 't.me/' in channel_url:
                channel_name = channel_url.split('t.me/')[1]
            else:
                channel_name = channel_url
            
            # Get the channel entity
            channel = await self.client.get_entity(channel_name)
            return channel
            
        except Exception as e:
            print(f"❌ Error getting channel entity for {channel_url}: {e}")
            return None
    
    async def get_channel_messages(self, channel_url: str, limit: int = CHANNEL_MESSAGE_LIMIT) -> List[Dict[str, Any]]:
        """Get messages from a Telegram channel using Telethon"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Get channel entity
            channel = await self.get_channel_entity(channel_url)
            if not channel:
                return []
            
            # Try to join the channel if needed
            try:
                await self.client(JoinChannelRequest(channel))
            except Exception as e:
                # Ignore join errors, we might already be a member or it might be public
                pass
            
            # Get messages
            messages = []
            async for message in self.client.iter_messages(channel, limit=limit):
                if not message or not message.message:  # Skip empty or non-text messages
                    continue
                
                messages.append({
                    'id': message.id,
                    'text': message.message,
                    'date': message.date,
                    'html': message.message,  # Telethon doesn't provide HTML by default
                    'channel_name': channel.username or str(channel.id),
                    'channel_id': channel.id,
                })
            
            return messages
            
        except Exception as e:
            print(f"❌ Error getting channel messages: {e}")
            return []
    
    async def send_message(self, channel: str, message_text: str) -> Optional[int]:
        """Send a message to a channel"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Get channel entity
            channel_entity = await self.get_channel_entity(channel)
            if not channel_entity:
                return None
            
            # Send message
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
        """Edit a message in a channel"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Get channel entity
            channel_entity = await self.get_channel_entity(channel)
            if not channel_entity:
                return False
            
            # Edit message
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
        """Get pinned messages from a channel"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Get channel entity
            channel_entity = await self.get_channel_entity(channel)
            if not channel_entity:
                return []
            
            # Get channel messages
            messages = await self.client.get_messages(channel_entity, pinned=True)
            return [msg.id for msg in messages if msg]
            
        except Exception as e:
            print(f"❌ Error getting pinned messages from {channel}: {e}")
            return []
    
    async def pin_message(self, channel: str, message_id: int) -> bool:
        """Pin a message in a channel"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Get channel entity
            channel_entity = await self.get_channel_entity(channel)
            if not channel_entity:
                return False
            
            # Pin message
            await self.client.pin_message(channel_entity, message_id)
            return True
            
        except Exception as e:
            print(f"❌ Error pinning message {message_id} in {channel}: {e}")
            return False 