import re
import asyncio
import html
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from src.telegram_client import TelegramClient
from config.channels import TELEGRAM_CHANNELS
from src.utils import async_retry_on_timeout


class ChannelScraper:
    
    def __init__(self, telegram_client: TelegramClient):
        self.telegram_client = telegram_client
        self.target_channels = TELEGRAM_CHANNELS
        self.proxy_keywords = [
            'proxy', 'mtproto', 'socks5', 'socks', 'http', 'https',
            'tg://', 't.me/proxy', 't.me/socks', 'server', 'port', 'secret',
            'ip:', 'host:', 'address:', 'telegram proxy', 'vpn', 'connect',
            'обход блокировки', 'прокси', 'телеграм', 'подключение'  # Russian keywords
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
    
    @async_retry_on_timeout(max_retries=5, delay=2.0)
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
            if not message or not hasattr(message, 'date'):
                continue
            
            if message.date < cutoff_date:
                continue
            
            # Extract all <a> tags and their href attributes
            message_data = self.extract_full_message_data(message)
            
            # Only include messages with href attributes or proxy keywords
            if message_data['hrefs'] or self.is_message_containing_proxy(message_data['combined_text']):
                relevant_messages.append({
                    'id': message.id,
                    'date': message.date,
                    'text': message_data['text'],
                    'html': message_data['html'],
                    'hrefs': message_data['hrefs'],
                    'combined_text': message_data['combined_text'],
                    'channel': message.chat.username if hasattr(message.chat, 'username') else 'unknown'
                })
        
        return relevant_messages
    
    def extract_full_message_data(self, message: Any):
        if not message:
            return {'text': '', 'html': '', 'hrefs': [], 'combined_text': ''}
        
        text = ""
        html_content = ""
        hrefs = []
        
        if hasattr(message, 'message') and message.message:
            text = message.message
        elif hasattr(message, 'text') and message.text:
            text = message.text
        
        # Get HTML content if available
        if hasattr(message, 'html') and message.html:
            html_content = message.html
            
            # Extract all href attributes from <a> tags in HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            for a_tag in soup.find_all('a'):
                href = a_tag.get('href')
                if href:
                    hrefs.append(href)
        
        # If no BeautifulSoup extraction, try with regex as fallback
        if not hrefs and html_content:
            href_pattern = r'<a [^>]*href=["\']([^"\']+)["\'][^>]*>'
            href_matches = re.finditer(href_pattern, html_content, re.IGNORECASE)
            for match in href_matches:
                href = match.group(1)
                if href:
                    hrefs.append(href)
        
        # Combine all text sources for keyword matching
        combined_text = text + " " + html_content
        
        return {
            'text': text.strip(),
            'html': html_content,
            'hrefs': hrefs,
            'combined_text': combined_text.strip()
        }
    
    def is_message_containing_proxy(self, message_text: str):
        if not message_text:
            return False
        
        text_lower = message_text.lower()
        
        for keyword in self.proxy_keywords:
            if keyword in text_lower:
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