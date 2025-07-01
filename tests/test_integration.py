import unittest
import asyncio
import json
import os
import sqlite3
import tempfile
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# Mock the Telethon import before importing our modules
mock_telethon = MagicMock()
mock_telethon.TelegramClient = MagicMock
mock_telethon.errors = MagicMock()
mock_telethon.errors.SessionPasswordNeededError = Exception
mock_telethon.errors.FloodWaitError = Exception
mock_telethon.tl = MagicMock()
mock_telethon.tl.functions = MagicMock()
mock_telethon.tl.functions.channels = MagicMock()
mock_telethon.tl.functions.channels.UpdatePinnedMessageRequest = MagicMock()
mock_telethon.tl.functions.messages = MagicMock()
mock_telethon.tl.functions.messages.GetHistoryRequest = MagicMock()
mock_telethon.tl.types = MagicMock()

# Set up all the mock modules
sys.modules['telethon'] = mock_telethon
sys.modules['telethon.errors'] = mock_telethon.errors
sys.modules['telethon.tl'] = mock_telethon.tl
sys.modules['telethon.tl.functions'] = mock_telethon.tl.functions
sys.modules['telethon.tl.functions.channels'] = mock_telethon.tl.functions.channels
sys.modules['telethon.tl.functions.messages'] = mock_telethon.tl.functions.messages
sys.modules['telethon.tl.types'] = mock_telethon.tl.types

# Import the modules after mocking
from src.scheduler import ProxyScheduler
from src.telegram_client import TelegramClient
from src.channel_scraper import ChannelScraper
from src.proxy_extractor import ProxyExtractor
from src.proxy_validator import ProxyValidator
from src.proxy_storage import ProxyStorage
from src.proxy_extractor import ProxyData

# Create a test version of ProxyStorage that uses our temp files
class TestProxyStorage(ProxyStorage):
    def __init__(self, db_path, storage_path, telegram_client=None, output_channel=None):
        self.storage_path = Path(storage_path)
        self.db_path = Path(db_path)
        self.telegram_client = telegram_client
        # Always set an output channel for testing
        self.output_channel = output_channel or "test_channel"
        self.last_posted_message_id = None
        self._ensure_storage_directories()
        self._initialize_database()
    
    # Override this method to always return True for testing
    async def post_proxies_to_telegram(self, proxies):
        # Call the original method to ensure it's tracked by the mock
        result = await super().post_proxies_to_telegram(proxies)
        return result or 12345  # Return a message ID even if the original method doesn't


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Create temporary files for testing
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_json_file = tempfile.NamedTemporaryFile(delete=False)
        
        # Close the files so they can be reopened by the code under test
        self.temp_db_file.close()
        self.temp_json_file.close()
        
        # Create a patcher for the ProxyStorage class in the scheduler
        self.proxy_storage_patcher = patch('src.scheduler.ProxyStorage')
        mock_proxy_storage_class = self.proxy_storage_patcher.start()
        
        # Configure the mock to return our test class instance
        def create_test_storage(*args, **kwargs):
            return TestProxyStorage(
                db_path=self.temp_db_file.name,
                storage_path=self.temp_json_file.name,
                telegram_client=kwargs.get('telegram_client'),
                output_channel=kwargs.get('output_channel')
            )
        
        mock_proxy_storage_class.side_effect = create_test_storage
        
        # Sample data
        self.sample_messages = [
            {
                'id': 1,
                'channel_id': 1001234567,
                'channel_name': 'test_channel',
                'date': '2023-01-01 12:00:00',
                'text': 'MTProto proxy: proxy.example.com:443 secret=7jK9dF3hGqW8sT5rY2xC1pL4mN6bV0aZ',
                'combined_text': 'MTProto proxy: proxy.example.com:443 secret=7jK9dF3hGqW8sT5rY2xC1pL4mN6bV0aZ'
            },
            {
                'id': 2,
                'channel_id': 1001234568,
                'channel_name': 'test_channel2',
                'date': '2023-01-01 13:00:00',
                'text': 'SOCKS5 proxy: socks5://user:pass@socks.example.com:1080',
                'combined_text': 'SOCKS5 proxy: socks5://user:pass@socks.example.com:1080'
            },
            {
                'id': 3,
                'channel_id': 1001234569,
                'channel_name': 'test_channel3',
                'date': '2023-01-01 14:00:00',
                'text': 'HTTP proxy: http://proxy.example.org:8080',
                'combined_text': 'HTTP proxy: http://proxy.example.org:8080'
            }
        ]
        
        self.extracted_proxies = [
            ProxyData(
                proxy_type='mtproto',
                server='proxy.example.com',
                port='443',
                secret='7jK9dF3hGqW8sT5rY2xC1pL4mN6bV0aZ',
                original_url='tg://proxy?server=proxy.example.com&port=443&secret=7jK9dF3hGqW8sT5rY2xC1pL4mN6bV0aZ'
            ),
            ProxyData(
                proxy_type='socks5',
                server='socks.example.com',
                port='1080',
                username='user',
                password='pass',
                original_url='tg://socks?server=socks.example.com&port=1080&user=user&pass=pass'
            ),
            ProxyData(
                proxy_type='http',
                server='proxy.example.org',
                port='8080',
                original_url='tg://http?server=proxy.example.org&port=8080'
            )
        ]
        
        # For validated proxies, we'll use the same ProxyData objects
        # The validator would normally add metadata but that's handled by the mock
        self.validated_proxies = [
            self.extracted_proxies[0],
            self.extracted_proxies[2]
        ]

    def tearDown(self):
        # Remove temporary files
        try:
            os.unlink(self.temp_db_file.name)
        except:
            pass
            
        try:
            os.unlink(self.temp_json_file.name)
        except:
            pass
        
        # Stop patchers
        self.proxy_storage_patcher.stop()

    @patch('src.telegram_client.TelegramClient.start_session')
    @patch('src.telegram_client.TelegramClient.close_session')
    @patch('src.channel_scraper.ChannelScraper.scrape_all_channels')
    @patch('src.proxy_extractor.ProxyExtractor.extract_all_proxies')
    @patch('src.proxy_validator.ProxyValidator.validate_all_proxies')
    @patch('src.proxy_storage.ProxyStorage.post_proxies_to_telegram')
    async def test_full_workflow(self, mock_post, mock_validate, mock_extract, 
                                mock_scrape, mock_close, mock_start):
        """Test the entire workflow from scraping to posting"""
        
        # Configure mocks
        mock_start.return_value = None
        mock_close.return_value = None
        mock_scrape.return_value = self.sample_messages
        
        # Configure extract to return different proxies for each message
        def extract_side_effect(text):
            if "MTProto" in text:
                return [self.extracted_proxies[0]]
            elif "SOCKS5" in text:
                return [self.extracted_proxies[1]]
            elif "HTTP" in text:
                return [self.extracted_proxies[2]]
            return []
            
        mock_extract.side_effect = extract_side_effect
        mock_validate.return_value = self.validated_proxies
        mock_post.return_value = 12345  # Message ID
        
        # Create scheduler with all components
        with patch('src.scheduler.OUTPUT_CHANNEL', 'test_channel'):
            scheduler = ProxyScheduler()
            
            # Run a single cycle
            await scheduler.run_single_cycle()
        
        # Verify the workflow
        mock_start.assert_called_once()
        mock_scrape.assert_called_once()
        self.assertEqual(mock_extract.call_count, 3)  # Called for each message
        mock_validate.assert_called_once()
        mock_post.assert_called_once()
        mock_close.assert_called_once()
        
        # Verify the data was saved to JSON
        with open(self.temp_json_file.name, 'r') as f:
            saved_data = json.load(f)
            # The data is in a different format than expected - it has 'proxies' key
            self.assertEqual(saved_data['total_proxies'], 2)  # Two validated proxies
            self.assertEqual(len(saved_data['proxies']), 2)  # Two validated proxies
    
    @patch('src.telegram_client.TelegramClient.start_session')
    @patch('src.telegram_client.TelegramClient.close_session')
    @patch('src.channel_scraper.ChannelScraper.scrape_all_channels')
    async def test_workflow_no_messages(self, mock_scrape, mock_close, mock_start):
        """Test workflow when no messages are found"""
        
        # Configure mocks
        mock_start.return_value = None
        mock_close.return_value = None
        mock_scrape.return_value = []
        
        # Create scheduler
        scheduler = ProxyScheduler()
        
        # Run a single cycle
        await scheduler.run_single_cycle()
        
        # Verify the workflow stops after scraping
        mock_start.assert_called_once()
        mock_scrape.assert_called_once()
        mock_close.assert_called_once()
    
    @patch('src.telegram_client.TelegramClient.start_session')
    @patch('src.telegram_client.TelegramClient.close_session')
    @patch('src.channel_scraper.ChannelScraper.scrape_all_channels')
    @patch('src.proxy_extractor.ProxyExtractor.extract_all_proxies')
    async def test_workflow_no_proxies_extracted(self, mock_extract, mock_scrape, 
                                              mock_close, mock_start):
        """Test workflow when no proxies are extracted"""
        
        # Configure mocks
        mock_start.return_value = None
        mock_close.return_value = None
        mock_scrape.return_value = self.sample_messages
        mock_extract.return_value = []
        
        # Create scheduler
        scheduler = ProxyScheduler()
        
        # Run a single cycle
        await scheduler.run_single_cycle()
        
        # Verify the workflow stops after extraction
        mock_start.assert_called_once()
        mock_scrape.assert_called_once()
        self.assertEqual(mock_extract.call_count, 3)  # Called for each message
        mock_close.assert_called_once()
    
    @patch('src.telegram_client.TelegramClient.start_session')
    @patch('src.telegram_client.TelegramClient.close_session')
    @patch('src.channel_scraper.ChannelScraper.scrape_all_channels')
    @patch('src.proxy_extractor.ProxyExtractor.extract_all_proxies')
    @patch('src.proxy_validator.ProxyValidator.validate_all_proxies')
    async def test_workflow_no_valid_proxies(self, mock_validate, mock_extract, 
                                          mock_scrape, mock_close, mock_start):
        """Test workflow when no proxies are valid"""
        
        # Configure mocks
        mock_start.return_value = None
        mock_close.return_value = None
        mock_scrape.return_value = self.sample_messages
        
        def extract_side_effect(text):
            if "MTProto" in text:
                return [self.extracted_proxies[0]]
            elif "SOCKS5" in text:
                return [self.extracted_proxies[1]]
            elif "HTTP" in text:
                return [self.extracted_proxies[2]]
            return []
            
        mock_extract.side_effect = extract_side_effect
        mock_validate.return_value = []  # No valid proxies
        
        # Create scheduler
        scheduler = ProxyScheduler()
        
        # Run a single cycle
        await scheduler.run_single_cycle()
        
        # Verify the workflow stops after validation
        mock_start.assert_called_once()
        mock_scrape.assert_called_once()
        self.assertEqual(mock_extract.call_count, 3)  # Called for each message
        mock_validate.assert_called_once()
        mock_close.assert_called_once()
    
    @patch('src.telegram_client.TelegramClient.start_session')
    @patch('src.telegram_client.TelegramClient.close_session')
    @patch('src.channel_scraper.ChannelScraper.scrape_all_channels', 
           side_effect=Exception("Network error"))
    async def test_workflow_with_exception(self, mock_scrape, mock_close, mock_start):
        """Test workflow when an exception occurs"""
        
        # Configure mocks
        mock_start.return_value = None
        mock_close.return_value = None
        
        # Create scheduler
        scheduler = ProxyScheduler()
        
        # Run a single cycle
        await scheduler.run_single_cycle()
        
        # Verify session is closed even when exception occurs
        mock_start.assert_called_once()
        mock_scrape.assert_called_once()
        mock_close.assert_called_once()


if __name__ == '__main__':
    unittest.main() 