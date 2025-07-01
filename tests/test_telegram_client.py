import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os
import requests

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.telegram_client import TelegramClient


class TestTelegramClient(unittest.TestCase):
    
    def setUp(self):
        self.client = TelegramClient()
    
    def tearDown(self):
        self.client = None
    
    @patch('src.telegram_client.Bot')
    def test_init_with_bot_token(self, mock_bot):
        with patch('src.telegram_client.BOT_TOKEN', 'test_token'):
            client = TelegramClient()
            mock_bot.assert_called_once_with(token='test_token')
            self.assertTrue(client.use_bot_token)
    
    @patch('src.telegram_client.Bot')
    def test_init_without_bot_token(self, mock_bot):
        with patch('src.telegram_client.BOT_TOKEN', None):
            client = TelegramClient()
            mock_bot.assert_not_called()
            self.assertFalse(client.use_bot_token)
    
    @patch('src.telegram_client.Bot')
    def test_start_session_with_bot(self, mock_bot):
        mock_bot_instance = AsyncMock()
        mock_bot_instance.get_me = AsyncMock(return_value=Mock(username='test_bot'))
        mock_bot.return_value = mock_bot_instance
        
        with patch('src.telegram_client.BOT_TOKEN', 'test_token'):
            client = TelegramClient()
            
            async def run_test():
                await client.start_session()
                self.assertTrue(client.is_connected)
                mock_bot_instance.get_me.assert_called_once()
            
            asyncio.run(run_test())
    
    def test_start_session_without_bot(self):
        with patch('src.telegram_client.BOT_TOKEN', None):
            client = TelegramClient()
            
            async def run_test():
                await client.start_session()
                self.assertTrue(client.is_connected)
            
            asyncio.run(run_test())
    
    def test_close_session(self):
        client = TelegramClient()
        client.is_connected = True
        
        async def run_test():
            await client.close_session()
            self.assertFalse(client.is_connected)
        
        asyncio.run(run_test())
    
    @patch('requests.Session.get')
    def test_get_channel_messages(self, mock_get):
        # Create a mock response with HTML content
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.text = '''
        <div class="tgme_widget_message" data-post="channel/123">
            <div class="tgme_widget_message_text">Test message</div>
            <span class="tgme_widget_message_date"><time datetime="2023-01-01T12:00:00+00:00"></time></span>
        </div>
        '''
        mock_get.return_value = mock_response
        
        client = TelegramClient()
        client.is_connected = True
        
        async def run_test():
            messages = await client.get_channel_messages('test_channel')
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0]['text'], 'Test message')
            mock_get.assert_called_once_with('https://t.me/s/test_channel')
        
        asyncio.run(run_test())
    
    @patch('src.telegram_client.Bot')
    def test_send_message(self, mock_bot):
        mock_bot_instance = AsyncMock()
        mock_message = Mock()
        mock_message.message_id = 123
        mock_bot_instance.send_message = AsyncMock(return_value=mock_message)
        mock_bot_instance.get_me = AsyncMock()
        mock_bot.return_value = mock_bot_instance
        
        with patch('src.telegram_client.BOT_TOKEN', 'test_token'):
            client = TelegramClient()
            client.is_connected = True
            
            async def run_test():
                message_id = await client.send_message('test_channel', 'Test message')
                self.assertEqual(message_id, 123)
                mock_bot_instance.send_message.assert_called_once_with(
                    chat_id='test_channel',
                    text='Test message',
                    parse_mode='Markdown'
                )
            
            asyncio.run(run_test())
    
    @patch('src.telegram_client.Bot')
    def test_pin_message(self, mock_bot):
        mock_bot_instance = AsyncMock()
        mock_bot_instance.pin_chat_message = AsyncMock()
        mock_bot_instance.get_me = AsyncMock()
        mock_bot.return_value = mock_bot_instance
        
        with patch('src.telegram_client.BOT_TOKEN', 'test_token'):
            client = TelegramClient()
            client.is_connected = True
            
            async def run_test():
                success = await client.pin_message('test_channel', 123)
                self.assertTrue(success)
                mock_bot_instance.pin_chat_message.assert_called_once_with(
                    chat_id='test_channel',
                    message_id=123,
                    disable_notification=True
                )
            
            asyncio.run(run_test())
    
    def test_get_channel_entity(self):
        client = TelegramClient()
        client.is_connected = True
        
        async def run_test():
            entity = await client.get_channel_entity('https://t.me/test_channel')
            self.assertEqual(entity['id'], 'test_channel')
            self.assertEqual(entity['username'], 'test_channel')
        
        asyncio.run(run_test())
    
    @patch('src.telegram_client.TelegramClient.get_channel_messages')
    def test_fetch_channel_messages(self, mock_get_messages):
        mock_get_messages.return_value = [
            {
                'id': '123',
                'channel_name': 'test_channel',
                'date': '2023-01-01 12:00:00',
                'text': 'Test message'
            }
        ]
        
        client = TelegramClient()
        client.is_connected = True
        
        async def run_test():
            channel_entity = {'username': 'test_channel'}
            messages = await client.fetch_channel_messages(channel_entity)
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0].id, '123')
            self.assertEqual(messages[0].message, 'Test message')
        
        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main() 