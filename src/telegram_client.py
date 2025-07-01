import requests
from bs4 import BeautifulSoup
import re
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from telegram import Bot
from config.settings import API_ID, API_HASH, PHONE_NUMBER, SESSION_NAME, RATE_LIMIT_DELAY, BOT_TOKEN


class TelegramClient:
    
    def __init__(self):
        self.bot = None if not BOT_TOKEN else Bot(token=BOT_TOKEN)
        self.session = requests.Session()
        self.is_connected = False
        self.use_bot_token = bool(BOT_TOKEN)
        
        # Configure headers to mimic a browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
    
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
    
    async def get_channel_messages(self, channel_url, limit=100):
        """
        Get messages from a Telegram channel using web scraping
        """
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
            
            # Make the request
            response = self.session.get(url)
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
                            
                            # Debug print for proxy links
                            if 't.me/proxy' in href:
                                print(f"Found proxy link in href: {href}")
                
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
    
    async def fetch_channel_messages(self, channel_entity, limit=100):
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