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
    API_ID, API_HASH, PHONE_NUMBER, SESSION_NAME, RATE_LIMIT_DELAY, BOT_TOKEN,
    CHANNEL_MESSAGE_LIMIT, USE_PROXY_FOR_SCRAPING, SCRAPING_PROXY_TIMEOUT,
    INITIAL_PROXY
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
        
        # Initialize bot with proxy if configured
        self.bot = None
        if BOT_TOKEN:
            self._init_bot_with_proxy()
    
    async def start_session(self):
        if self.is_connected:
            return
        
        try:
            if self.use_bot_token and self.bot:
                # Test the bot connection by getting bot info
                bot_info = await self.bot.get_me()
                self.is_connected = True
                print(f"✅ Connected to Telegram as bot: {bot_info.username}")
            else:
                # For web scraping, we don't need authentication
                self.is_connected = True
                print("✅ Ready for web scraping")
            
        except Exception as e:
            print(f"❌ Error connecting to Telegram: {e}")
            self.is_connected = False
    
    async def close_session(self):
        if self.bot:
            # Nothing to close for the bot
            pass
        self.is_connected = False
    
    def set_proxy_storage(self, proxy_storage):
        """Set the proxy storage instance for accessing working proxies"""
        self.proxy_storage = proxy_storage
        # Re-initialize bot with potential new proxies
        if self.use_bot_token:
            self._init_bot_with_proxy()
    
    def _init_bot_with_proxy(self):
        """Initialize the Telegram bot with proxy configuration"""
        try:
            # Get proxy configuration
            proxy = self._get_initial_proxy()
            if not proxy:
                proxy = self._get_working_proxy_for_scraping()
            
            if proxy:
                # Configure proxy for bot
                proxy_url = None
                if proxy.proxy_type == 'http':
                    proxy_url = f"http://{proxy.server}:{proxy.port}"
                elif proxy.proxy_type == 'socks5':
                    proxy_url = f"socks5://{proxy.server}:{proxy.port}"
                    if proxy.username and proxy.password:
                        proxy_url = f"socks5://{proxy.username}:{proxy.password}@{proxy.server}:{proxy.port}"
                elif proxy.proxy_type == 'mtproto':
                    # Skip MTProto proxies for bot API as they're not directly supported
                    print("ℹ️ MTProto proxies are not supported for Bot API, skipping proxy configuration")
                    proxy_url = None
                
                if proxy_url:
                    # Create proxy-enabled request object
                    proxy_request = HTTPXRequest(
                        connection_pool_size=8,
                        proxy=proxy_url,
                        read_timeout=SCRAPING_PROXY_TIMEOUT,
                        write_timeout=SCRAPING_PROXY_TIMEOUT,
                        connect_timeout=SCRAPING_PROXY_TIMEOUT
                    )
                    
                    # Initialize bot with proxy
                    self.bot = Bot(token=BOT_TOKEN, request=proxy_request)
                    print(f"🔗 Initialized bot with {proxy.proxy_type} proxy: {proxy.server}:{proxy.port}")
                    return
            
            # If no proxy or proxy setup failed, initialize without proxy
            self.bot = Bot(token=BOT_TOKEN)
            print("ℹ️ Initialized bot without proxy")
            
        except Exception as e:
            print(f"⚠️ Error initializing bot with proxy: {e}")
            # Fallback to no proxy
            self.bot = Bot(token=BOT_TOKEN)
            print("ℹ️ Fallback: Initialized bot without proxy")
    
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
                # For MTProto proxies, we'll use HTTPS proxy configuration
                # This allows us to use the proxy for web scraping
                proxy_url = f"http://{proxy.server}:{proxy.port}"
                if proxy.secret:
                    # Add the secret as a basic auth password
                    proxy_url = f"http://mtproto:{proxy.secret}@{proxy.server}:{proxy.port}"
                self.session.proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
            
            # Set timeout for proxy requests
            self.session.timeout = config.settings.SCRAPING_PROXY_TIMEOUT
            self.current_proxy = proxy
            
        except Exception as e:
            print(f"❌ Error configuring proxy: {e}")
            self.session.proxies.clear()
            self.current_proxy = None
    
    async def get_channel_messages(self, channel_url, limit=CHANNEL_MESSAGE_LIMIT):
        """
        Get messages from a Telegram channel using web scraping
        """
        if not self.is_connected:
            await self.start_session()
        
        # Configure proxy for scraping if enabled
        if USE_PROXY_FOR_SCRAPING and not self.current_proxy:
            proxy = self._get_working_proxy_for_scraping()
            self._configure_session_proxy(proxy)
        
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
                
                # Get the full HTML content of the message
                html_content = str(text_div) if text_div else ''
                
                # Get message date
                date_span = container.find('span', class_='tgme_widget_message_date')
                date_str = date_span.find('time').get('datetime') if date_span and date_span.find('time') else ''
                date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00')) if date_str else datetime.now()
                
                # Extract all href attributes from a tags
                hrefs = []
                if text_div:
                    for a_tag in text_div.find_all('a'):
                        href = a_tag.get('href')
                        if href:
                            hrefs.append(href)
                
                # Create message data structure
                message_data = {
                    'id': message_id,
                    'channel_id': channel_name,
                    'channel_name': channel_name,
                    'date': date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                    'text': text,
                    'html': html_content,
                    'hrefs': hrefs,
                    'combined_text': text + ' ' + html_content
                }
                
                messages.append(message_data)
            
            return messages
            
        except Exception as e:
            # If proxy request failed, try without proxy
            if self.current_proxy and USE_PROXY_FOR_SCRAPING:
                print(f"⚠️ Proxy request failed ({e}), retrying without proxy...")
                self._configure_session_proxy(None)  # Clear proxy
                
                try:
                    # Retry without proxy
                    response = self.session.get(url, timeout=10)
                    response.raise_for_status()
                    
                    # Parse the HTML (same logic as above)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    message_containers = soup.find_all('div', class_='tgme_widget_message')
                    
                    messages = []
                    for container in message_containers[:limit]:
                        message_id = container.get('data-post', '').split('/')[-1]
                        
                        # Get message text
                        text_div = container.find('div', class_='tgme_widget_message_text')
                        text = text_div.get_text() if text_div else ''
                        
                        # Get the full HTML content of the message
                        html_content = str(text_div) if text_div else ''
                        
                        # Get message date
                        date_span = container.find('span', class_='tgme_widget_message_date')
                        date_str = date_span.find('time').get('datetime') if date_span and date_span.find('time') else ''
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00')) if date_str else datetime.now()
                        
                        # Extract all href attributes from a tags
                        hrefs = []
                        if text_div:
                            for a_tag in text_div.find_all('a'):
                                href = a_tag.get('href')
                                if href:
                                    hrefs.append(href)
                        
                        # Create message data structure
                        message_data = {
                            'id': message_id,
                            'channel_id': channel_name,
                            'channel_name': channel_name,
                            'date': date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                            'text': text,
                            'html': html_content,
                            'hrefs': hrefs,
                            'combined_text': text + ' ' + html_content
                        }
                        
                        messages.append(message_data)
                    
                    print(f"✅ Fallback request successful (without proxy)")
                    return messages
                    
                except Exception as fallback_error:
                    print(f"❌ Both proxy and direct requests failed: {fallback_error}")
                    return []
            else:
                print(f"❌ Error fetching messages from {channel_url}: {e}")
                return []
    
    async def send_message(self, channel, message_text):
        """
        Send a message to a Telegram channel using the bot
        """
        if not self.bot or not self.is_connected:
            await self.start_session()
        
        if not self.bot:
            print("❌ Bot token not configured. Cannot send messages.")
            return None
        
        try:
            message = await self.bot.send_message(
                chat_id=channel,
                text=message_text,
                parse_mode='Markdown'
            )
            return message.message_id
        except Exception as e:
            print(f"❌ Error sending message to {channel}: {e}")
            return None
    
    async def edit_message(self, channel, message_id, new_text):
        """
        Edit an existing message in a Telegram channel using the bot
        """
        if not self.bot or not self.is_connected:
            await self.start_session()
        
        if not self.bot:
            print("❌ Bot token not configured. Cannot edit messages.")
            return False
        
        try:
            await self.bot.edit_message_text(
                chat_id=channel,
                message_id=message_id,
                text=new_text,
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
        if not self.bot or not self.is_connected:
            await self.start_session()
        
        if not self.bot:
            print("❌ Bot token not configured. Cannot get pinned messages.")
            return []
        
        try:
            chat = await self.bot.get_chat(chat_id=channel)
            if chat.pinned_message:
                return [chat.pinned_message.message_id]
            else:
                return []
        except Exception as e:
            print(f"❌ Error getting pinned messages from {channel}: {e}")
            return []
    
    async def pin_message(self, channel, message_id):
        """
        Pin a message in a Telegram channel using the bot
        """
        if not self.bot or not self.is_connected:
            await self.start_session()
        
        if not self.bot:
            print("❌ Bot token not configured. Cannot pin messages.")
            return False
        
        try:
            await self.bot.pin_chat_message(
                chat_id=channel,
                message_id=message_id,
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