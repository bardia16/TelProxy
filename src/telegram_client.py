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
from config.settings import (
    BOT_TOKEN, CHANNEL_MESSAGE_LIMIT, USE_PROXY_FOR_SCRAPING,
    SCRAPING_PROXY_TIMEOUT, INITIAL_PROXY
)
import config.settings
from src.proxy_extractor import ProxyData


class TelegramClient:
    
    def __init__(self):
        self.session = requests.Session()
        self.is_connected = False
        self.use_bot_token = bool(BOT_TOKEN)
        self.current_proxy = None
        self.proxy_storage = None  # Will be set by scheduler if needed
        
        # Configure headers to mimic a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
        
        # Initialize session with proxy if configured
        self._init_session()
    
    def _init_session(self):
        """Initialize session with proxy configuration"""
        try:
            proxy = self._get_initial_proxy()
            if not proxy:
                proxy = self._get_working_proxy_for_scraping()
            
            if proxy:
                self._configure_session_proxy(proxy)
            
        except Exception as e:
            print(f"⚠️ Error initializing session: {e}")
            self._configure_session_proxy(None)
    
    def _configure_session_proxy(self, proxy=None):
        """Configure the requests session to use a proxy"""
        if not proxy:
            # Clear any existing proxy configuration
            self.session.proxies.clear()
            self.current_proxy = None
            return
        
        try:
            if proxy.proxy_type == 'http':
                proxy_url = f"http://{proxy.server}:{proxy.port}"
                self.session.proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
            elif proxy.proxy_type == 'socks5':
                proxy_url = f"socks5://{proxy.server}:{proxy.port}"
                if proxy.username and proxy.password:
                    proxy_url = f"socks5://{proxy.username}:{proxy.password}@{proxy.server}:{proxy.port}"
                self.session.proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
            elif proxy.proxy_type == 'mtproto':
                # For MTProto proxies, we'll try using HTTP proxy configuration
                # Some MTProto proxies can work this way for web scraping
                proxy_url = f"http://{proxy.server}:{proxy.port}"
                if proxy.secret:
                    # Add the secret as a query parameter
                    proxy_url = f"http://{proxy.server}:{proxy.port}?secret={proxy.secret}"
                self.session.proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
                # Set custom headers that might help with MTProto
                self.session.headers.update({
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                })
            
            # Set timeout for proxy requests
            self.session.timeout = config.settings.SCRAPING_PROXY_TIMEOUT
            self.current_proxy = proxy
            print(f"🔗 Configured session with {proxy.proxy_type} proxy: {proxy.server}:{proxy.port}")
            
        except Exception as e:
            print(f"❌ Error configuring proxy: {e}")
            self.session.proxies.clear()
            self.current_proxy = None
    
    async def start_session(self):
        if self.is_connected:
            return
        
        try:
            # Test the connection by making a request to Telegram
            response = self.session.get('https://t.me/', timeout=config.settings.SCRAPING_PROXY_TIMEOUT)
            response.raise_for_status()
            self.is_connected = True
            print("✅ Connected to Telegram web")
            
        except Exception as e:
            print(f"❌ Error connecting to Telegram: {e}")
            self.is_connected = False
            # Try reinitializing the session with a different proxy
            self._init_session()
    
    async def close_session(self):
        self.is_connected = False
    
    def set_proxy_storage(self, proxy_storage):
        """Set the proxy storage instance for accessing working proxies"""
        self.proxy_storage = proxy_storage
        # Re-initialize session with potential new proxies
        self._init_session()
    
    def _get_initial_proxy(self):
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
    
    def _get_working_proxy_for_scraping(self):
        """Get a working proxy for web scraping from the database or initial config"""
        if not USE_PROXY_FOR_SCRAPING:
            return None
        
        try:
            # First try to get the initial proxy since it's configured manually
            initial_proxy = self._get_initial_proxy()
            if initial_proxy:
                return initial_proxy
            
            # Then try to get a proxy from storage if available
            if self.proxy_storage:
                if config.settings.SCRAPING_PROXY_TYPE == 'auto':
                    # Try HTTP first, then SOCKS5
                    http_proxies = self.proxy_storage.get_proxies_by_type('http')
                    socks5_proxies = self.proxy_storage.get_proxies_by_type('socks5')
                    all_proxies = http_proxies + socks5_proxies
                else:
                    all_proxies = self.proxy_storage.get_proxies_by_type(config.settings.SCRAPING_PROXY_TYPE)
                
                if all_proxies:
                    # Return the first working proxy from storage
                    proxy = all_proxies[0]
                    print(f"🔗 Using stored {proxy.proxy_type} proxy: {proxy.server}:{proxy.port}")
                    return proxy
            
            print("⚠️ No working proxies found for scraping")
            return None
                
        except Exception as e:
            print(f"❌ Error getting proxy for scraping: {e}")
            return None
    
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
            
            # Make the request (with proxy if configured)
            response = self.session.get(url, timeout=config.settings.SCRAPING_PROXY_TIMEOUT)
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