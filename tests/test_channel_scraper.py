import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.channel_scraper import ChannelScraper
from src.telegram_client import TelegramClient


class TestChannelScraper(unittest.TestCase):
    
    def setUp(self):
        self.mock_telegram_client = Mock(spec=TelegramClient)
        self.scraper = ChannelScraper(self.mock_telegram_client)
    
    def tearDown(self):
        self.scraper = None
        self.mock_telegram_client = None
    
    def test_init(self):
        self.assertEqual(self.scraper.telegram_client, self.mock_telegram_client)
        self.assertIsInstance(self.scraper.target_channels, list)
        self.assertIsInstance(self.scraper.proxy_keywords, list)
        self.assertIn('proxy', self.scraper.proxy_keywords)
        self.assertIn('mtproto', self.scraper.proxy_keywords)
    
    def test_scrape_all_channels_success(self):
        test_channels = ['https://t.me/channel1', 'https://t.me/channel2']
        self.scraper.target_channels = test_channels
        
        mock_messages = [
            {'id': 1, 'text': 'proxy message', 'combined_text': 'proxy tg://proxy?server=1.1.1.1&port=443'},
            {'id': 2, 'text': 'socks message', 'combined_text': 'socks5 tg://socks?server=2.2.2.2&port=1080'}
        ]
        
        async def run_test():
            with patch.object(self.scraper, 'scrape_single_channel', new_callable=AsyncMock) as mock_scrape:
                with patch.object(self.scraper, 'filter_relevant_messages') as mock_filter:
                    with patch('asyncio.sleep', new_callable=AsyncMock):
                        
                        mock_scrape.side_effect = [mock_messages[:1], mock_messages[1:]]
                        mock_filter.side_effect = [mock_messages[:1], mock_messages[1:]]
                        
                        result = await self.scraper.scrape_all_channels()
                        
                        self.assertEqual(len(result), 2)
                        self.assertEqual(mock_scrape.call_count, 2)
                        mock_scrape.assert_any_call('https://t.me/channel1')
                        mock_scrape.assert_any_call('https://t.me/channel2')
        
        asyncio.run(run_test())
    
    def test_scrape_all_channels_with_failures(self):
        test_channels = ['https://t.me/channel1', 'https://t.me/channel2']
        self.scraper.target_channels = test_channels
        
        async def run_test():
            with patch.object(self.scraper, 'scrape_single_channel', new_callable=AsyncMock) as mock_scrape:
                with patch('asyncio.sleep', new_callable=AsyncMock):
                    
                    mock_scrape.side_effect = [Exception("Network error"), []]
                    
                    result = await self.scraper.scrape_all_channels()
                    
                    self.assertEqual(result, [])
                    self.assertEqual(mock_scrape.call_count, 2)
        
        asyncio.run(run_test())
    
    def test_scrape_single_channel_success(self):
        mock_entity = Mock()
        mock_messages = [Mock(), Mock()]
        
        self.mock_telegram_client.get_channel_entity = AsyncMock(return_value=mock_entity)
        self.mock_telegram_client.fetch_channel_messages = AsyncMock(return_value=mock_messages)
        
        async def run_test():
            result = await self.scraper.scrape_single_channel('https://t.me/test_channel')
            
            self.assertEqual(result, mock_messages)
            self.mock_telegram_client.get_channel_entity.assert_called_once_with('https://t.me/test_channel')
            self.mock_telegram_client.fetch_channel_messages.assert_called_once_with(mock_entity, limit=200)
        
        asyncio.run(run_test())
    
    def test_scrape_single_channel_no_entity(self):
        self.mock_telegram_client.get_channel_entity = AsyncMock(return_value=None)
        
        async def run_test():
            result = await self.scraper.scrape_single_channel('https://t.me/test_channel')
            
            self.assertEqual(result, [])
            self.mock_telegram_client.get_channel_entity.assert_called_once_with('https://t.me/test_channel')
        
        asyncio.run(run_test())
    
    def test_scrape_single_channel_exception(self):
        self.mock_telegram_client.get_channel_entity = AsyncMock(side_effect=Exception("API Error"))
        
        async def run_test():
            result = await self.scraper.scrape_single_channel('https://t.me/test_channel')
            
            self.assertEqual(result, [])
        
        asyncio.run(run_test())
    
    def test_filter_relevant_messages(self):
        current_time = datetime.now()
        old_time = current_time - timedelta(days=40)
        recent_time = current_time - timedelta(days=10)
        
        mock_chat = Mock()
        mock_chat.username = 'test_channel'
        
        mock_messages = [
            Mock(id=1, date=recent_time, chat=mock_chat),  # Recent with proxy
            Mock(id=2, date=old_time, chat=mock_chat),     # Too old
            Mock(id=3, date=recent_time, chat=mock_chat),  # Recent no proxy
            Mock(id=4, date=None, chat=mock_chat),         # No date
        ]
        
        # Mock datetime.now() to return our controlled current_time
        with patch('src.channel_scraper.datetime') as mock_datetime_module:
            mock_datetime_module.now.return_value = current_time
            mock_datetime_module.timedelta = timedelta
            
            with patch.object(self.scraper, 'extract_full_message_data') as mock_extract:
                with patch.object(self.scraper, 'is_message_containing_proxy') as mock_contains:
                    
                    mock_extract.side_effect = [
                        {'combined_text': 'proxy server message', 'text': 'proxy server message', 'urls': []},
                        {'combined_text': 'normal message', 'text': 'normal message', 'urls': []},
                        {'combined_text': '', 'text': '', 'urls': []}
                    ]
                    
                    mock_contains.side_effect = [True, False, False]
                    
                    result = self.scraper.filter_relevant_messages(mock_messages)
                    
                    self.assertEqual(len(result), 1)
                    self.assertEqual(result[0]['id'], 1)
                    self.assertEqual(result[0]['channel'], 'test_channel')
    
    def test_extract_full_message_data_basic_text(self):
        mock_message = Mock()
        mock_message.message = "Basic text message"
        mock_message.entities = None
        mock_message.reply_markup = None
        mock_message.buttons = None
        mock_message.web_preview = None
        
        result = self.scraper.extract_full_message_data(mock_message)
        
        self.assertEqual(result['text'], "Basic text message")
        self.assertEqual(result['urls'], [])
        self.assertEqual(result['combined_text'], "Basic text message")
    
    def test_extract_full_message_data_with_entities(self):
        from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
        
        mock_message = Mock()
        mock_message.message = "Check this link"
        mock_message.reply_markup = None
        mock_message.buttons = None
        mock_message.web_preview = None
        
        mock_entity1 = Mock(spec=MessageEntityTextUrl)
        mock_entity1.url = "https://example.com/proxy"
        mock_entity2 = Mock()
        mock_entity2.url = "https://another.com"
        
        mock_message.entities = [mock_entity1, mock_entity2]
        
        result = self.scraper.extract_full_message_data(mock_message)
        
        self.assertEqual(result['text'], "Check this link")
        self.assertIn("https://example.com/proxy", result['urls'])
        self.assertIn("https://another.com", result['urls'])
        self.assertIn("https://example.com/proxy", result['combined_text'])
    
    def test_extract_full_message_data_with_buttons(self):
        mock_message = Mock()
        mock_message.message = "Click button"
        mock_message.entities = None
        mock_message.web_preview = None
        
        # Button with URL (URL takes precedence over text)
        mock_button_url = Mock()
        mock_button_url.url = "tg://proxy?server=1.1.1.1&port=443"
        mock_button_url.text = "Connect"
        
        # Button with text only (no URL)
        mock_button_text = Mock()
        mock_button_text.url = None
        mock_button_text.text = "Info"
        
        mock_row = Mock()
        mock_row.buttons = [mock_button_url, mock_button_text]
        
        mock_reply_markup = Mock()
        mock_reply_markup.rows = [mock_row]
        
        mock_message.reply_markup = mock_reply_markup
        mock_message.buttons = None
        
        result = self.scraper.extract_full_message_data(mock_message)
        
        # URL button's text is NOT added (URL takes precedence)
        self.assertNotIn("Connect", result['text'])
        # Text-only button's text IS added
        self.assertIn("Info", result['text'])
        # URL is captured
        self.assertIn("tg://proxy?server=1.1.1.1&port=443", result['urls'])
        self.assertIn("tg://proxy?server=1.1.1.1&port=443", result['combined_text'])
    
    def test_extract_full_message_data_empty_message(self):
        result = self.scraper.extract_full_message_data(None)
        
        self.assertEqual(result['text'], '')
        self.assertEqual(result['urls'], [])
        self.assertEqual(result['combined_text'], '')
    
    def test_extract_message_text_delegates_to_full_data(self):
        mock_message = Mock()
        
        with patch.object(self.scraper, 'extract_full_message_data') as mock_extract:
            mock_extract.return_value = {'combined_text': 'combined result'}
            
            result = self.scraper.extract_message_text(mock_message)
            
            self.assertEqual(result, 'combined result')
            mock_extract.assert_called_once_with(mock_message)
    
    def test_is_message_containing_proxy_keywords(self):
        test_cases = [
            ("Check this proxy server", True),
            ("MTProto connection available", True),
            ("SOCKS5 proxy list", True),
            ("HTTP proxy settings", True),
            ("Connect via tg://", True),
            ("Visit t.me/proxy for access", True),
            ("Regular message without keywords", False),
            ("", False),
        ]
        
        for message, expected in test_cases:
            with self.subTest(message=message):
                result = self.scraper.is_message_containing_proxy(message)
                self.assertEqual(result, expected)
    
    def test_is_message_containing_proxy_patterns(self):
        test_cases = [
            ("tg://proxy?server=1.1.1.1&port=443", True),
            ("tg://socks?server=2.2.2.2&port=1080", True),
            ("t.me/proxy?server=3.3.3.3&port=8080", True),
            ("server=example.com and port=443", True),
            ("secret=abcdef123456", True),
            ("Connect to 192.168.1.1:8080", True),
            ("No patterns here at all", False),  # Changed to avoid keyword "proxy"
        ]
        
        for message, expected in test_cases:
            with self.subTest(message=message):
                result = self.scraper.is_message_containing_proxy(message)
                self.assertEqual(result, expected)
    
    def test_get_channel_name_from_url(self):
        test_cases = [
            ("https://t.me/test_channel", "test_channel"),
            ("t.me/another_channel", "another_channel"),
            ("@channel_name", "channel_name"),
            ("plain_channel", "plain_channel"),
            ("", "unknown"),
            (None, "unknown"),
        ]
        
        for url, expected in test_cases:
            with self.subTest(url=url):
                result = self.scraper.get_channel_name_from_url(url)
                self.assertEqual(result, expected)
    
    def test_extract_full_message_data_with_web_preview(self):
        mock_message = Mock()
        mock_message.message = "Check this out"
        mock_message.entities = None
        mock_message.reply_markup = None
        mock_message.buttons = None
        
        mock_web_preview = Mock()
        mock_web_preview.url = "https://proxy-site.com/list"
        mock_message.web_preview = mock_web_preview
        
        result = self.scraper.extract_full_message_data(mock_message)
        
        self.assertEqual(result['text'], "Check this out")
        self.assertIn("https://proxy-site.com/list", result['urls'])
        self.assertIn("https://proxy-site.com/list", result['combined_text'])
    
    def test_extract_full_message_data_text_attribute_fallback(self):
        mock_message = Mock()
        mock_message.message = None  # No message attribute
        mock_message.text = "Fallback text content"
        mock_message.entities = None
        mock_message.reply_markup = None
        mock_message.buttons = None
        mock_message.web_preview = None
        
        result = self.scraper.extract_full_message_data(mock_message)
        
        self.assertEqual(result['text'], "Fallback text content")
        self.assertEqual(result['combined_text'], "Fallback text content")


if __name__ == '__main__':
    unittest.main() 