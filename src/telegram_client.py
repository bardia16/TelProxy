import requests
from bs4 import BeautifulSoup
import re
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from telegram import Bot
from telegram.request import HTTPXRequest
import httpx
import socket
from config.settings import (
    BOT_TOKEN, CHANNEL_MESSAGE_LIMIT, USE_PROXY_FOR_SCRAPING,
    SCRAPING_PROXY_TIMEOUT
)
import config.settings
from src.proxy_extractor import ProxyData


class TelegramClient:
    # Local SOCKS5 proxy configuration (created by SSH tunnel)
    SOCKS5_PROXY = {
        'http': 'socks5h://127.0.0.1:1080',
        'https': 'socks5h://127.0.0.1:1080'
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.is_connected = False
        self.use_bot_token = bool(BOT_TOKEN)
        self.bot = None
        
        # Configure headers to mimic a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
        
        # Initialize session and bot with proxy
        self._init_session()
        if self.use_bot_token:
            self._init_bot()
    
    def _check_proxy_connection(self):
        """Check if the SOCKS5 proxy is available"""
        try:
            # Try to connect to the SOCKS proxy
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect(('127.0.0.1', 1080))
            sock.close()
            return True
        except (socket.timeout, socket.error):
            print("⚠️ Local SOCKS5 proxy not available. Make sure SSH tunnel is active:")
            print("   ssh -N -D 1080 user@server")
            return False
    
    def _init_session(self):
        """Initialize requests session with SOCKS5 proxy"""
        try:
            if not self._check_proxy_connection():
                return
            
            # Configure session to use SOCKS5 proxy
            self.session.proxies = self.SOCKS5_PROXY
            self.session.timeout = SCRAPING_PROXY_TIMEOUT
            
            # Test the connection
            response = self.session.get('https://t.me/', timeout=SCRAPING_PROXY_TIMEOUT)
            response.raise_for_status()
            print("✅ Successfully connected to Telegram web through SOCKS5 proxy")
            
        except Exception as e:
            print(f"❌ Error configuring session with SOCKS5 proxy: {e}")
            # Clear proxy configuration
            self.session.proxies.clear()
    
    def _init_bot(self):
        """Initialize Telegram bot with SOCKS5 proxy"""
        try:
            if not self._check_proxy_connection():
                return
            
            # Configure bot with SOCKS5 proxy
            proxy_request = HTTPXRequest(
                connection_pool_size=8,
                proxy=self.SOCKS5_PROXY['https'],
                read_timeout=SCRAPING_PROXY_TIMEOUT,
                write_timeout=SCRAPING_PROXY_TIMEOUT,
                connect_timeout=SCRAPING_PROXY_TIMEOUT
            )
            
            self.bot = Bot(token=BOT_TOKEN, request=proxy_request)
            print("✅ Successfully configured bot with SOCKS5 proxy")
            
        except Exception as e:
            print(f"❌ Error configuring bot with SOCKS5 proxy: {e}")
            # Initialize bot without proxy as fallback
            self.bot = Bot(token=BOT_TOKEN)
            print("ℹ️ Fallback: Initialized bot without proxy")
    
    async def start_session(self):
        if self.is_connected:
            return
        
        try:
            if self.use_bot_token and self.bot:
                # Test the bot connection
                bot_info = await self.bot.get_me()
                self.is_connected = True
                print(f"✅ Connected to Telegram as bot: {bot_info.username}")
            else:
                # For web scraping only, we don't need bot authentication
                self.is_connected = True
                print("✅ Ready for web scraping")
            
        except Exception as e:
            print(f"❌ Error connecting to Telegram: {e}")
            self.is_connected = False
            # Try reinitializing the session
            self._init_session()
            if self.use_bot_token:
                self._init_bot()
    
    async def close_session(self):
        self.is_connected = False
    
    async def get_channel_messages(self, channel_url, limit=CHANNEL_MESSAGE_LIMIT):
        """Get messages from a Telegram channel using web scraping"""
        if not self.is_connected:
            await self.start_session()
        
        try:
            # Clean up the channel URL
            if '@' in channel_url:
                channel_name = channel_url.replace('@', '')
                url = f"https://t.me/s/{channel_name}"
            elif 't.me/' in channel_url:
                channel_name = channel_url.split('t.me/')[1]
                url = f"https://t.me/s/{channel_name}"
            else:
                channel_name = channel_url
                url = f"https://t.me/s/{channel_name}"
            
            # Make the request through SOCKS5 proxy
            response = self.session.get(url, timeout=SCRAPING_PROXY_TIMEOUT)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all message containers
            message_containers = soup.find_all('div', class_='tgme_widget_message')
            
            messages = []
            for container in message_containers[:limit]:
                message_id = container.get('data-post', '').split('/')[-1]
                
                # Get message text
                text_div = container.find('div', class_='tgme_widget_message_text')
                text = text_div.get_text() if text_div else ''
                
                # Get message date
                date_span = container.find('span', class_='tgme_widget_message_date')
                date_str = date_span.find('time').get('datetime') if date_span and date_span.find('time') else ''
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00')) if date_str else datetime.now()
                
                # Create message data structure
                message_data = {
                    'id': message_id,
                    'text': text,
                    'date': date_obj
                }
                
                messages.append(message_data)
            
            return messages
            
        except Exception as e:
            print(f"❌ Error getting channel messages: {e}")
            # If proxy request failed, try reinitializing the session
            self._init_session()
            return []
    
    async def send_message(self, channel, message_text):
        """
        Send a message to a Telegram channel using the bot
        """
        if not self.telethon_client or not self.is_connected:
            await self.start_session()
        
        try:
            message = await self.telethon_client.send_message(
                channel,
                message_text,
                parse_mode='Markdown'
            )
            return message.id
        except Exception as e:
            print(f"❌ Error sending message to {channel}: {e}")
            return None
    
    async def edit_message(self, channel, message_id, new_text):
        """
        Edit an existing message in a Telegram channel using the bot
        """
        if not self.telethon_client or not self.is_connected:
            await self.start_session()
        
        try:
            await self.telethon_client.edit_message(
                channel,
                message_id,
                None,
                new_text,
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            print(f"❌ Error editing message {message_id} in {channel}: {e}")
            return False
    
    async def get_pinned_messages(self, channel):
        """
        Get pinned messages from a Telegram channel using the bot
        """
        if not self.telethon_client or not self.is_connected:
            await self.start_session()
        
        try:
            chat = await self.telethon_client.get_chat(chat_id=channel)
            if chat.pinned_message:
                return [chat.pinned_message.id]
            else:
                return []
        except Exception as e:
            print(f"❌ Error getting pinned messages from {channel}: {e}")
            return []
    
    async def pin_message(self, channel, message_id):
        """
        Pin a message in a Telegram channel using the bot
        """
        if not self.telethon_client or not self.is_connected:
            await self.start_session()
        
        try:
            await self.telethon_client.pin_message(
                channel,
                message_id,
                disable_notification=True
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