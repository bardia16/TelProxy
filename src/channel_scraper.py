import re
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from src.telegram_client import TelegramClient
from config.channels import TELEGRAM_CHANNELS


class ChannelScraper:
    
    def __init__(self, telegram_client: TelegramClient):
        self.telegram_client = telegram_client
        self.target_channels = TELEGRAM_CHANNELS
        self.proxy_keywords = [
            'proxy', 'mtproto', 'socks5', 'socks', 'http', 'https',
            'tg://', 't.me/proxy', 't.me/socks', 'server', 'port', 'secret'
        ]
    
    async def scrape_all_channels(self):
        all_messages = []
        successful_channels = 0
        
        for channel_url in self.target_channels:
            print(f"Scraping channel: {self.get_channel_name_from_url(channel_url)}")
            
            try:
                messages = await self.scrape_single_channel(channel_url)
                if messages:
                    relevant_messages = self.filter_relevant_messages(messages)
                    all_messages.extend(relevant_messages)
                    successful_channels += 1
                    print(f"Found {len(relevant_messages)} relevant messages")
                
                await asyncio.sleep(2)
                
            except Exception as e:
                print(f"Failed to scrape {channel_url}: {e}")
                continue
        
        print(f"Successfully scraped {successful_channels}/{len(self.target_channels)} channels")
        print(f"Total relevant messages found: {len(all_messages)}")
        return all_messages
    
    async def scrape_single_channel(self, channel_url: str):
        try:
            channel_entity = await self.telegram_client.get_channel_entity(channel_url)
            if not channel_entity:
                return []
            
            messages = await self.telegram_client.fetch_channel_messages(
                channel_entity, limit=200
            )
            
            return messages
            
        except Exception as e:
            print(f"Error scraping channel {channel_url}: {e}")
            return []
    
    def filter_relevant_messages(self, messages: List[Any]):
        relevant_messages = []
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for message in messages:
            if not message or not message.date:
                continue
            
            if message.date < cutoff_date:
                continue
            
            message_text = self.extract_message_text(message)
            if message_text and self.is_message_containing_proxy(message_text):
                relevant_messages.append({
                    'id': message.id,
                    'date': message.date,
                    'text': message_text,
                    'channel': message.chat.username if hasattr(message.chat, 'username') else 'unknown'
                })
        
        return relevant_messages
    
    def extract_message_text(self, message: Any):
        if not message:
            return ""
        
        text = ""
        if hasattr(message, 'message') and message.message:
            text = message.message
        elif hasattr(message, 'text') and message.text:
            text = message.text
        
        if hasattr(message, 'entities') and message.entities:
            for entity in message.entities:
                if hasattr(entity, 'url') and entity.url:
                    text += f" {entity.url}"
        
        return text.strip()
    
    def is_message_containing_proxy(self, message_text: str):
        if not message_text:
            return False
        
        text_lower = message_text.lower()
        
        for keyword in self.proxy_keywords:
            if keyword in text_lower:
                return True
        
        proxy_patterns = [
            r'tg://proxy\?',
            r'tg://socks\?',
            r'tg://http\?',
            r't\.me/proxy\?',
            r't\.me/socks\?',
            r'server=[\w\.]',
            r'port=\d+',
            r'secret=[a-fA-F0-9]+',
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+'
        ]
        
        for pattern in proxy_patterns:
            if re.search(pattern, message_text, re.IGNORECASE):
                return True
        
        return False
    
    def get_channel_name_from_url(self, channel_url: str):
        if not channel_url:
            return "unknown"
        
        if 't.me/' in channel_url:
            return channel_url.split('/')[-1]
        elif '@' in channel_url:
            return channel_url.replace('@', '')
        else:
            return channel_url 