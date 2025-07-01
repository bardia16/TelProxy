import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.telegram_client import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError


class TestTelegramClient(unittest.TestCase):
    
    def setUp(self):
        self.client = TelegramClient()
    
    def tearDown(self):
        self.client = None
    
    @patch('src.telegram_client.API_ID', '12345')
    @patch('src.telegram_client.API_HASH', 'test_hash')
    @patch('src.telegram_client.TelethonClient')
    def test_initialize_connection_success(self, mock_telethon_client):
        mock_client_instance = AsyncMock()
        mock_client_instance.connect = AsyncMock()
        mock_client_instance.is_user_authorized = AsyncMock(return_value=True)
        mock_telethon_client.return_value = mock_client_instance
        
        async def run_test():
            await self.client.initialize_connection()
            
            mock_telethon_client.assert_called_once()
            mock_client_instance.connect.assert_called_once()
            mock_client_instance.is_user_authorized.assert_called_once()
            self.assertTrue(self.client.is_authenticated)
        
        asyncio.run(run_test())
    
    @patch('src.telegram_client.API_ID', None)
    @patch('src.telegram_client.API_HASH', None)
    def test_initialize_connection_missing_credentials(self):
        async def run_test():
            with self.assertRaises(ValueError) as context:
                await self.client.initialize_connection()
            self.assertIn("API_ID and API_HASH must be configured", str(context.exception))
        
        asyncio.run(run_test())
    
    @patch('src.telegram_client.API_ID', '12345')
    @patch('src.telegram_client.API_HASH', 'test_hash')
    @patch('src.telegram_client.PHONE_NUMBER', '+1234567890')
    @patch('src.telegram_client.TelethonClient')
    @patch('builtins.input', side_effect=['123456'])
    def test_authenticate_user_success(self, mock_input, mock_telethon_client):
        mock_client_instance = AsyncMock()
        mock_client_instance.connect = AsyncMock()
        mock_client_instance.is_user_authorized = AsyncMock(return_value=False)
        mock_client_instance.send_code_request = AsyncMock()
        mock_client_instance.sign_in = AsyncMock()
        mock_telethon_client.return_value = mock_client_instance
        
        self.client.client = mock_client_instance
        
        async def run_test():
            await self.client.authenticate_user()
            
            mock_client_instance.send_code_request.assert_called_once_with('+1234567890')
            mock_client_instance.sign_in.assert_called_once_with('+1234567890', '123456')
            self.assertTrue(self.client.is_authenticated)
        
        asyncio.run(run_test())
    
    @patch('src.telegram_client.API_ID', '12345')
    @patch('src.telegram_client.API_HASH', 'test_hash')  
    @patch('src.telegram_client.PHONE_NUMBER', '+1234567890')
    @patch('src.telegram_client.TelethonClient')
    @patch('builtins.input', side_effect=['123456', 'test_password'])
    def test_authenticate_user_with_2fa(self, mock_input, mock_telethon_client):
        mock_client_instance = AsyncMock()
        mock_client_instance.connect = AsyncMock()
        mock_client_instance.is_user_authorized = AsyncMock(return_value=False)
        mock_client_instance.send_code_request = AsyncMock()
        mock_client_instance.sign_in = AsyncMock(side_effect=[SessionPasswordNeededError("2FA required"), None])
        mock_telethon_client.return_value = mock_client_instance
        
        self.client.client = mock_client_instance
        
        async def run_test():
            await self.client.authenticate_user()
            
            self.assertEqual(mock_client_instance.sign_in.call_count, 2)
            mock_client_instance.sign_in.assert_any_call('+1234567890', '123456')
            mock_client_instance.sign_in.assert_any_call(password='test_password')
            self.assertTrue(self.client.is_authenticated)
        
        asyncio.run(run_test())
    
    @patch('src.telegram_client.PHONE_NUMBER', None)
    def test_authenticate_user_missing_phone(self):
        mock_client_instance = AsyncMock()
        mock_client_instance.is_user_authorized = AsyncMock(return_value=False)
        self.client.client = mock_client_instance
        
        async def run_test():
            with self.assertRaises(ValueError) as context:
                await self.client.authenticate_user()
            self.assertIn("PHONE_NUMBER must be configured", str(context.exception))
        
        asyncio.run(run_test())
    
    @patch('src.telegram_client.TelethonClient')
    def test_start_session(self, mock_telethon_client):
        mock_client_instance = AsyncMock()
        mock_client_instance.connect = AsyncMock()
        mock_client_instance.is_user_authorized = AsyncMock(return_value=True)
        mock_client_instance.start = AsyncMock()
        mock_telethon_client.return_value = mock_client_instance
        
        async def run_test():
            with patch.object(self.client, 'initialize_connection', new_callable=AsyncMock) as mock_init:
                with patch.object(self.client, 'authenticate_user', new_callable=AsyncMock) as mock_auth:
                    self.client.is_authenticated = True
                    self.client.client = mock_client_instance  # Set the client instance
                    await self.client.start_session()
                    
                    mock_init.assert_called_once()
                    mock_auth.assert_not_called()  # Already authenticated
                    mock_client_instance.start.assert_called_once()
        
        asyncio.run(run_test())
    
    def test_close_session(self):
        mock_client_instance = AsyncMock()
        mock_client_instance.is_connected = Mock(return_value=True)
        mock_client_instance.disconnect = AsyncMock()
        self.client.client = mock_client_instance
        self.client.is_authenticated = True
        
        async def run_test():
            await self.client.close_session()
            
            mock_client_instance.disconnect.assert_called_once()
            self.assertFalse(self.client.is_authenticated)
        
        asyncio.run(run_test())
    
    def test_get_channel_entity_success(self):
        mock_client_instance = AsyncMock()
        mock_entity = Mock()
        mock_client_instance.get_entity = AsyncMock(return_value=mock_entity)
        
        self.client.client = mock_client_instance
        self.client.is_authenticated = True
        
        async def run_test():
            result = await self.client.get_channel_entity('https://t.me/test_channel')
            
            self.assertEqual(result, mock_entity)
            mock_client_instance.get_entity.assert_called_once_with('https://t.me/test_channel')
        
        asyncio.run(run_test())
    
    def test_get_channel_entity_not_authenticated(self):
        self.client.is_authenticated = False
        
        async def run_test():
            with self.assertRaises(RuntimeError) as context:
                await self.client.get_channel_entity('https://t.me/test_channel')
            self.assertIn("Client must be authenticated", str(context.exception))
        
        asyncio.run(run_test())
    
    def test_fetch_channel_messages_success(self):
        mock_client_instance = AsyncMock()
        mock_messages = [Mock(), Mock(), Mock()]
        
        async def mock_iter_messages(*args, **kwargs):
            for msg in mock_messages:
                yield msg
        
        mock_client_instance.iter_messages = mock_iter_messages
        
        self.client.client = mock_client_instance
        self.client.is_authenticated = True
        
        async def run_test():
            with patch('asyncio.sleep', new_callable=AsyncMock):
                result = await self.client.fetch_channel_messages(Mock(), limit=100)
                
                self.assertEqual(len(result), 3)
                self.assertEqual(result, mock_messages)
        
        asyncio.run(run_test())
    
    def test_fetch_channel_messages_flood_wait(self):
        mock_client_instance = AsyncMock()
        
        # Create a proper FloodWaitError mock with seconds attribute
        flood_error = FloodWaitError("Too many requests")
        flood_error.seconds = 10
        
        async def mock_iter_messages_with_flood(*args, **kwargs):
            raise flood_error
            yield  # This will never be reached but makes it an async generator
        
        mock_client_instance.iter_messages = mock_iter_messages_with_flood
        
        self.client.client = mock_client_instance
        self.client.is_authenticated = True
        
        async def run_test():
            with patch('src.telegram_client.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                result = await self.client.fetch_channel_messages(Mock(), limit=100)
                
                self.assertEqual(result, [])
                mock_sleep.assert_called_with(10)
        
        asyncio.run(run_test())
    
    def test_is_connected_true(self):
        mock_client_instance = Mock()
        mock_client_instance.is_connected.return_value = True
        self.client.client = mock_client_instance
        self.client.is_authenticated = True
        
        result = self.client.is_connected()
        self.assertTrue(result)
    
    def test_is_connected_false_no_client(self):
        self.client.client = None
        self.client.is_authenticated = True
        
        result = self.client.is_connected()
        self.assertFalse(result)
    
    def test_is_connected_false_not_authenticated(self):
        mock_client_instance = Mock()
        mock_client_instance.is_connected.return_value = True
        self.client.client = mock_client_instance
        self.client.is_authenticated = False
        
        result = self.client.is_connected()
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main() 