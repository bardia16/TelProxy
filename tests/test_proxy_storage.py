import unittest
import asyncio
import json
import sqlite3
import os
import shutil
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, mock_open
from pathlib import Path
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Mock the UpdatePinnedMessageRequest import
sys.modules['telethon.tl.functions.channels'] = MagicMock()
sys.modules['telethon.tl.functions.channels'].UpdatePinnedMessageRequest = MagicMock()

from src.proxy_extractor import ProxyData

# Only import ProxyStorage after mocking the imports
with patch('src.proxy_storage.UpdatePinnedMessageRequest', MagicMock()):
    from src.proxy_storage import ProxyStorage


class TestProxyStorage(unittest.TestCase):
    
    def setUp(self):
        # Use test paths to avoid touching real data
        self.test_storage_path = 'data/test_proxies.json'
        self.test_db_path = 'data/test_proxies.db'
        
        # Delete any existing test database
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        # Make sure data directory exists
        os.makedirs(os.path.dirname(self.test_db_path), exist_ok=True)
        
        # Patch storage path for initialization
        with patch('src.proxy_storage.STORAGE_FILE_PATH', self.test_storage_path):
            # Create ProxyStorage with mocked client
            self.mock_telegram_client = Mock()
            self.mock_telegram_client.client = AsyncMock()
            self.storage = ProxyStorage(
                telegram_client=self.mock_telegram_client,
                output_channel='test_channel'
            )
            
            # Override db_path directly
            self.storage.db_path = Path(self.test_db_path)
            
            # Explicitly initialize the database
            self.storage._initialize_database()
        
        # Create some test proxy data
        self.test_proxies = [
            ProxyData(proxy_type='mtproto', server='1.1.1.1', port='443', secret='abcdef'),
            ProxyData(proxy_type='socks5', server='2.2.2.2', port='1080', username='user', password='pass'),
            ProxyData(proxy_type='http', server='3.3.3.3', port='8080')
        ]
    
    def tearDown(self):
        # Clean up test files
        try:
            if os.path.exists(self.test_storage_path):
                os.remove(self.test_storage_path)
            if os.path.exists(self.test_db_path):
                os.remove(self.test_db_path)
            if os.path.exists('data/test'):
                shutil.rmtree('data/test')
        except (OSError, PermissionError) as e:
            print(f"Error during cleanup: {e}")
    
    def test_init(self):
        """Test initialization of ProxyStorage"""
        self.assertEqual(str(self.storage.storage_path), self.test_storage_path)
        self.assertEqual(str(self.storage.db_path), self.test_db_path)
        self.assertEqual(self.storage.telegram_client, self.mock_telegram_client)
        self.assertEqual(self.storage.output_channel, 'test_channel')
        self.assertIsNone(self.storage.last_posted_message_id)
    
    def test_ensure_storage_directories(self):
        """Test directory creation"""
        # Create a non-existent path for testing
        test_path = 'data/test/proxies.json'
        storage = ProxyStorage()
        storage.storage_path = Path(test_path)
        
        # Call the method
        storage._ensure_storage_directories()
        
        # Check that the directories were created
        self.assertTrue(os.path.exists('data/test'))
    
    def test_initialize_database(self):
        """Test database initialization"""
        # Make sure the database file exists
        self.assertTrue(os.path.exists(self.test_db_path))
        
        # Check if tables were created
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            
            # Check proxies table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='proxies'")
            self.assertIsNotNone(cursor.fetchone())
            
            # Check posting_history table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posting_history'")
            self.assertIsNotNone(cursor.fetchone())
    
    def test_save_proxies_to_json(self):
        """Test saving proxies to JSON file"""
        # Mock the json module to capture the dumped data
        mock_json_dump = MagicMock()
        with patch('json.dump', mock_json_dump):
            self.storage.save_proxies_to_json(self.test_proxies)
        
        # Check that json.dump was called with the correct data
        args, kwargs = mock_json_dump.call_args
        dumped_data = args[0]
        self.assertEqual(dumped_data['total_proxies'], 3)
        self.assertEqual(len(dumped_data['proxies']), 3)
    
    def test_load_proxies_from_json_nonexistent(self):
        """Test loading proxies from a nonexistent JSON file"""
        # Ensure the file doesn't exist
        if os.path.exists(self.test_storage_path):
            os.remove(self.test_storage_path)
        
        # Try to load
        proxies = self.storage.load_proxies_from_json()
        
        # Should return empty list
        self.assertEqual(proxies, [])
    
    def test_load_proxies_from_json_existing(self):
        """Test loading proxies from an existing JSON file"""
        # Create test data
        test_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_proxies': 2,
            'proxies': [
                {
                    'proxy_type': 'mtproto',
                    'server': '1.1.1.1',
                    'port': '443',
                    'secret': 'abcdef',
                    'username': None,
                    'password': None,
                    'original_url': 'tg://proxy?server=1.1.1.1&port=443&secret=abcdef'
                },
                {
                    'proxy_type': 'socks5',
                    'server': '2.2.2.2',
                    'port': '1080',
                    'username': 'user',
                    'password': 'pass',
                    'original_url': 'tg://socks?server=2.2.2.2&port=1080&user=user&pass=pass'
                }
            ]
        }
        
        # Write test data to file
        os.makedirs(os.path.dirname(self.test_storage_path), exist_ok=True)
        with open(self.test_storage_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        # Load the data
        proxies = self.storage.load_proxies_from_json()
        
        # Check results
        self.assertEqual(len(proxies), 2)
        self.assertEqual(proxies[0].proxy_type, 'mtproto')
        self.assertEqual(proxies[0].server, '1.1.1.1')
        self.assertEqual(proxies[0].port, '443')
        self.assertEqual(proxies[0].secret, 'abcdef')
        self.assertEqual(proxies[1].proxy_type, 'socks5')
        self.assertEqual(proxies[1].username, 'user')
        self.assertEqual(proxies[1].password, 'pass')
    
    def test_load_proxies_from_json_error(self):
        """Test loading proxies when JSON is invalid"""
        # Write invalid JSON
        os.makedirs(os.path.dirname(self.test_storage_path), exist_ok=True)
        with open(self.test_storage_path, 'w', encoding='utf-8') as f:
            f.write("This is not valid JSON")
        
        # Should return empty list on error
        proxies = self.storage.load_proxies_from_json()
        self.assertEqual(proxies, [])
    
    def test_save_proxies_to_database(self):
        """Test saving proxies to the database"""
        self.storage.save_proxies_to_database(self.test_proxies)
        
        # Check if proxies were saved
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM proxies')
            count = cursor.fetchone()[0]
            self.assertEqual(count, 3)
    
    def test_load_proxies_from_database_all(self):
        """Test loading all proxies from database"""
        # Save some data
        self.storage.save_proxies_to_database(self.test_proxies)
        
        # Load all proxies
        proxies = self.storage.load_proxies_from_database(working_only=False)
        
        # Check results
        self.assertEqual(len(proxies), 3)
    
    def test_load_proxies_from_database_by_type(self):
        """Test loading proxies by type"""
        # Save some data
        self.storage.save_proxies_to_database(self.test_proxies)
        
        # Load mtproto proxies only
        proxies = self.storage.load_proxies_from_database(proxy_type='mtproto')
        
        # Check results
        self.assertEqual(len(proxies), 1)
        self.assertEqual(proxies[0].proxy_type, 'mtproto')
    
    def test_update_proxy_status(self):
        """Test updating proxy status"""
        # Save some data
        self.storage.save_proxies_to_database(self.test_proxies)
        
        # Update status of one proxy
        proxy = self.test_proxies[0]
        self.storage.update_proxy_status(proxy, False)
        
        # Check the status
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT is_working FROM proxies WHERE server = ? AND port = ?',
                (proxy.server, proxy.port)
            )
            is_working = cursor.fetchone()[0]
            self.assertEqual(is_working, 0)  # SQLite stores booleans as 0/1
    
    def test_get_working_proxies(self):
        """Test getting only working proxies"""
        # Save some data
        self.storage.save_proxies_to_database(self.test_proxies)
        
        # Set one proxy as not working
        proxy = self.test_proxies[0]
        self.storage.update_proxy_status(proxy, False)
        
        # Get working proxies
        proxies = self.storage.get_working_proxies()
        
        # Should return only 2 proxies
        self.assertEqual(len(proxies), 2)
    
    def test_get_proxies_by_type(self):
        """Test getting proxies by type"""
        # Save some data
        self.storage.save_proxies_to_database(self.test_proxies)
        
        # Get HTTP proxies
        proxies = self.storage.get_proxies_by_type('http')
        
        # Should return 1 proxy
        self.assertEqual(len(proxies), 1)
        self.assertEqual(proxies[0].proxy_type, 'http')
    
    def test_remove_outdated_proxies(self):
        """Test removing outdated proxies"""
        # Save some data
        self.storage.save_proxies_to_database(self.test_proxies)
        
        # Modify the timestamp of one proxy to make it old
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            old_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                'UPDATE proxies SET last_validated = ? WHERE server = ?',
                (old_date, self.test_proxies[0].server)
            )
            conn.commit()
        
        # Remove proxies older than 14 days
        removed = self.storage.remove_outdated_proxies(days_old=14)
        
        # Should remove 1 proxy
        self.assertEqual(removed, 1)
        
        # Check count
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM proxies')
            count = cursor.fetchone()[0]
            self.assertEqual(count, 2)
    
    def test_export_proxies_to_text(self):
        """Test exporting proxies to text file"""
        # Save some data
        self.storage.save_proxies_to_database(self.test_proxies)
        
        # Set up mock
        m = mock_open()
        with patch('builtins.open', m):
            self.storage.export_proxies_to_text('test_export.txt')
        
        # Check that the file was opened for writing
        m.assert_called_once_with('test_export.txt', 'w', encoding='utf-8')
        
        # Check content
        handle = m()
        written_content = ''.join(call.args[0] for call in handle.write.call_args_list)
        self.assertIn('# Telegram Proxies Export', written_content)
        self.assertIn('# Total working proxies: 3', written_content)
        self.assertIn('## MTPROTO', written_content)
        self.assertIn('## SOCKS5', written_content)
        self.assertIn('## HTTP', written_content)
    
    def test_reconstruct_proxy_url(self):
        """Test URL reconstruction for different proxy types"""
        # MTProto proxy
        mtproto_proxy = ProxyData(proxy_type='mtproto', server='1.1.1.1', port='443', secret='abcdef')
        url = self.storage._reconstruct_proxy_url(mtproto_proxy)
        self.assertEqual(url, 'tg://proxy?server=1.1.1.1&port=443&secret=abcdef')
        
        # Socks5 proxy
        socks5_proxy = ProxyData(
            proxy_type='socks5', 
            server='2.2.2.2', 
            port='1080', 
            username='user', 
            password='pass'
        )
        url = self.storage._reconstruct_proxy_url(socks5_proxy)
        self.assertEqual(url, 'tg://socks?server=2.2.2.2&port=1080&user=user&pass=pass')
        
        # HTTP proxy
        http_proxy = ProxyData(proxy_type='http', server='3.3.3.3', port='8080')
        url = self.storage._reconstruct_proxy_url(http_proxy)
        self.assertEqual(url, 'tg://http?server=3.3.3.3&port=8080')
        
        # Unknown type
        unknown_proxy = ProxyData(proxy_type='unknown', server='4.4.4.4', port='9999')
        url = self.storage._reconstruct_proxy_url(unknown_proxy)
        self.assertEqual(url, '4.4.4.4:9999')
    
    def test_format_proxy_message(self):
        """Test formatting proxy message for Telegram"""
        message = self.storage._format_proxy_message(self.test_proxies)
        
        # Check basic formatting
        self.assertIn('**Hourly Proxy Update**', message)
        self.assertIn('**Total Proxies:** 3', message)
        self.assertIn('**MTPROTO (1):**', message)
        self.assertIn('**SOCKS5 (1):**', message)
        self.assertIn('**HTTP (1):**', message)
        self.assertIn('*Next update in 1 hour*', message)
    
    def test_record_posting_history(self):
        """Test recording posting history to database"""
        # Record a post
        self.storage._record_posting_history(12345, 10)
        
        # Check the record
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT message_id, proxy_count, channel_id FROM posting_history')
            record = cursor.fetchone()
            
            self.assertEqual(record[0], 12345)  # message_id
            self.assertEqual(record[1], 10)     # proxy_count
            self.assertEqual(record[2], 'test_channel')  # channel_id
    
    def test_get_posting_stats(self):
        """Test getting posting statistics"""
        # Add some history records
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                'INSERT INTO posting_history (message_id, proxy_count, channel_id, posted_at) VALUES (?, ?, ?, ?)',
                (12345, 10, 'test_channel', now)
            )
            cursor.execute(
                'INSERT INTO posting_history (message_id, proxy_count, channel_id, posted_at) VALUES (?, ?, ?, ?)',
                (12346, 15, 'test_channel', yesterday)
            )
            conn.commit()
        
        # Get stats
        stats = self.storage.get_posting_stats(days=7)
        
        # Check results
        self.assertEqual(stats['total_posts'], 2)
        self.assertEqual(stats['total_proxies'], 25)
        self.assertEqual(stats['avg_proxies_per_post'], 12.5)
        self.assertIsNotNone(stats['last_post'])
    
    async def async_test_post_proxies_to_telegram(self):
        """Test posting proxies to Telegram"""
        # Configure mock
        send_message_mock = AsyncMock()
        send_message_mock.return_value = Mock(id=12345)
        self.mock_telegram_client.client.send_message = send_message_mock
        
        # Mock the _pin_latest_message method to avoid calling actual implementation
        with patch.object(self.storage, '_pin_latest_message', AsyncMock()) as pin_mock:
            # Call the method
            message_id = await self.storage.post_proxies_to_telegram(self.test_proxies)
            
            # Check that send_message was called
            send_message_mock.assert_called_once()
            self.assertEqual(message_id, 12345)
            
            # Check pin was called
            pin_mock.assert_called_once_with(12345)
    
    def test_post_proxies_to_telegram(self):
        """Test wrapper for async post_proxies_to_telegram"""
        asyncio.run(self.async_test_post_proxies_to_telegram())
    
    async def async_test_post_proxies_to_telegram_no_client(self):
        """Test posting proxies when client is not configured"""
        # Create storage without client
        storage = ProxyStorage()
        
        # Call the method
        message_id = await storage.post_proxies_to_telegram(self.test_proxies)
        
        # Should return None
        self.assertIsNone(message_id)
    
    def test_post_proxies_to_telegram_no_client(self):
        """Test wrapper for async post_proxies_to_telegram_no_client"""
        asyncio.run(self.async_test_post_proxies_to_telegram_no_client())
    
    async def async_test_post_proxies_to_telegram_exception(self):
        """Test exception handling when posting to Telegram"""
        # Configure mock to raise exception
        self.mock_telegram_client.client.send_message = AsyncMock(side_effect=Exception("Test error"))
        
        # Call the method
        message_id = await self.storage.post_proxies_to_telegram(self.test_proxies)
        
        # Should return None on error
        self.assertIsNone(message_id)
    
    def test_post_proxies_to_telegram_exception(self):
        """Test wrapper for async post_proxies_to_telegram_exception"""
        asyncio.run(self.async_test_post_proxies_to_telegram_exception())
    
    async def async_test_pin_latest_message(self):
        """Test pinning messages in Telegram"""
        # Configure mock
        self.mock_telegram_client.client = AsyncMock()
        
        # Call the method
        await self.storage._pin_latest_message(12345)
        
        # Check that the API was called
        self.mock_telegram_client.client.assert_called()
        self.assertEqual(self.storage.last_posted_message_id, 12345)
    
    def test_pin_latest_message(self):
        """Test wrapper for async pin_latest_message"""
        asyncio.run(self.async_test_pin_latest_message())
    
    async def async_test_pin_latest_message_with_previous(self):
        """Test pinning messages when there was a previous pin"""
        # Set a previous message ID
        self.storage.last_posted_message_id = 11111
        
        # Configure mock
        self.mock_telegram_client.client = AsyncMock()
        
        # Call the method
        await self.storage._pin_latest_message(12345)
        
        # Check that the API was called twice (unpin and pin)
        self.assertEqual(self.mock_telegram_client.client.call_count, 2)
        self.assertEqual(self.storage.last_posted_message_id, 12345)
    
    def test_pin_latest_message_with_previous(self):
        """Test wrapper for async pin_latest_message_with_previous"""
        asyncio.run(self.async_test_pin_latest_message_with_previous())
    
    async def async_test_pin_latest_message_exception(self):
        """Test exception handling when pinning messages"""
        # Configure mock to raise exception
        self.mock_telegram_client.client = AsyncMock(side_effect=Exception("Test error"))
        
        # Call the method - should not raise exception
        await self.storage._pin_latest_message(12345)
        
        # The method should handle the exception
        self.mock_telegram_client.client.assert_called_once()
    
    def test_pin_latest_message_exception(self):
        """Test wrapper for async pin_latest_message_exception"""
        asyncio.run(self.async_test_pin_latest_message_exception())


if __name__ == '__main__':
    unittest.main() 