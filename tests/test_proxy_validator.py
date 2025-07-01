import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os
import aiohttp

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.proxy_validator import ProxyValidator
from src.proxy_extractor import ProxyData


class TestProxyValidator(unittest.TestCase):
    
    def setUp(self):
        self.validator = ProxyValidator()
    
    def tearDown(self):
        self.validator = None
    
    def test_init(self):
        self.assertIsNotNone(self.validator.timeout)
        self.assertIsInstance(self.validator.validation_results, dict)
        self.assertIsNotNone(self.validator.test_url)
        self.assertIsInstance(self.validator.telegram_test_domains, list)
    
    async def async_test_validate_all_proxies_empty_list(self):
        proxies = []
        results = await self.validator.validate_all_proxies(proxies)
        
        self.assertEqual(len(results), 0)
    
    def test_validate_all_proxies_empty_list(self):
        asyncio.run(self.async_test_validate_all_proxies_empty_list())
    
    @patch('src.proxy_validator.ProxyValidator.validate_single_proxy')
    async def async_test_validate_all_proxies_success(self, mock_validate_proxy):
        # Create proxies for testing
        proxies = [
            ProxyData(proxy_type='mtproto', server='1.1.1.1', port='443', secret='abcdef'),
            ProxyData(proxy_type='socks5', server='2.2.2.2', port='1080', username='user', password='pass'),
            ProxyData(proxy_type='http', server='3.3.3.3', port='8080')
        ]
        
        # Configure mock results
        mock_validate_proxy.side_effect = [True, True, True]
        
        # Run validation
        results = await self.validator.validate_all_proxies(proxies)
        
        # Check results
        self.assertEqual(len(results), 3)
        self.assertEqual(len(self.validator.validation_results), 3)
        for proxy_key, is_valid in self.validator.validation_results.items():
            self.assertTrue(is_valid)
    
    def test_validate_all_proxies_success(self):
        asyncio.run(self.async_test_validate_all_proxies_success())
    
    @patch('src.proxy_validator.ProxyValidator.validate_single_proxy')
    async def async_test_validate_all_proxies_mixed_results(self, mock_validate_proxy):
        # Create proxies for testing
        proxies = [
            ProxyData(proxy_type='mtproto', server='1.1.1.1', port='443', secret='abcdef'),
            ProxyData(proxy_type='socks5', server='2.2.2.2', port='1080', username='user', password='pass'),
            ProxyData(proxy_type='http', server='3.3.3.3', port='8080')
        ]
        
        # Configure mock results - some pass, some fail
        mock_validate_proxy.side_effect = [True, False, True]
        
        # Run validation
        results = await self.validator.validate_all_proxies(proxies)
        
        # Check results
        self.assertEqual(len(results), 2)  # Only 2 working proxies
        self.assertEqual(len(self.validator.validation_results), 3)  # All tested
        self.assertTrue(self.validator.validation_results.get('1.1.1.1:443'))
        self.assertFalse(self.validator.validation_results.get('2.2.2.2:1080'))
        self.assertTrue(self.validator.validation_results.get('3.3.3.3:8080'))
    
    def test_validate_all_proxies_mixed_results(self):
        asyncio.run(self.async_test_validate_all_proxies_mixed_results())
    
    @patch('src.proxy_validator.ProxyValidator.validate_single_proxy')
    async def async_test_validate_all_proxies_with_exceptions(self, mock_validate_proxy):
        # Create proxies for testing
        proxies = [
            ProxyData(proxy_type='mtproto', server='1.1.1.1', port='443', secret='abcdef'),
            ProxyData(proxy_type='socks5', server='2.2.2.2', port='1080', username='user', password='pass'),
            ProxyData(proxy_type='http', server='3.3.3.3', port='8080')
        ]
        
        # Configure mock results with an exception
        mock_validate_proxy.side_effect = [True, Exception("Connection error"), True]
        
        # Run validation
        results = await self.validator.validate_all_proxies(proxies)
        
        # Check results
        self.assertEqual(len(results), 2)  # Only 2 working proxies
        self.assertEqual(len(self.validator.validation_results), 3)  # All tested
        self.assertTrue(self.validator.validation_results.get('1.1.1.1:443'))
        self.assertFalse(self.validator.validation_results.get('2.2.2.2:1080'))
        self.assertTrue(self.validator.validation_results.get('3.3.3.3:8080'))
    
    def test_validate_all_proxies_with_exceptions(self):
        asyncio.run(self.async_test_validate_all_proxies_with_exceptions())
    
    @patch('src.proxy_validator.ProxyValidator.test_mtproto_connectivity')
    async def async_test_validate_single_proxy_mtproto_success(self, mock_test):
        # Configure mock
        mock_test.return_value = True
        
        proxy = ProxyData(
            proxy_type='mtproto',
            server='1.1.1.1',
            port='443',
            secret='abcdef123456'
        )
        
        result = await self.validator.validate_single_proxy(proxy)
        self.assertTrue(result)
    
    def test_validate_single_proxy_mtproto_success(self):
        asyncio.run(self.async_test_validate_single_proxy_mtproto_success())
    
    @patch('src.proxy_validator.ProxyValidator.test_mtproto_connectivity')
    async def async_test_validate_single_proxy_mtproto_failure(self, mock_test):
        # Configure mock
        mock_test.return_value = False
        
        proxy = ProxyData(
            proxy_type='mtproto',
            server='1.1.1.1',
            port='443',
            secret='abcdef123456'
        )
        
        result = await self.validator.validate_single_proxy(proxy)
        self.assertFalse(result)
    
    def test_validate_single_proxy_mtproto_failure(self):
        asyncio.run(self.async_test_validate_single_proxy_mtproto_failure())
    
    @patch('src.proxy_validator.ProxyValidator.test_mtproto_connectivity')
    async def async_test_validate_single_proxy_mtproto_exception(self, mock_test):
        # Configure mock
        mock_test.side_effect = Exception("Connection failed")
        
        proxy = ProxyData(
            proxy_type='mtproto',
            server='1.1.1.1',
            port='443',
            secret='abcdef123456'
        )
        
        result = await self.validator.validate_single_proxy(proxy)
        self.assertFalse(result)
    
    def test_validate_single_proxy_mtproto_exception(self):
        asyncio.run(self.async_test_validate_single_proxy_mtproto_exception())
    
    @patch('src.proxy_validator.ProxyValidator.test_socks5_connectivity')
    async def async_test_validate_single_proxy_socks5_success(self, mock_test):
        # Configure mock
        mock_test.return_value = True
        
        proxy = ProxyData(
            proxy_type='socks5',
            server='2.2.2.2',
            port='1080',
            username='user',
            password='pass'
        )
        
        result = await self.validator.validate_single_proxy(proxy)
        self.assertTrue(result)
    
    def test_validate_single_proxy_socks5_success(self):
        asyncio.run(self.async_test_validate_single_proxy_socks5_success())
    
    @patch('src.proxy_validator.ProxyValidator.test_socks5_connectivity')
    async def async_test_validate_single_proxy_socks5_failure(self, mock_test):
        # Configure mock
        mock_test.side_effect = Exception("Connection failed")
        
        proxy = ProxyData(
            proxy_type='socks5',
            server='2.2.2.2',
            port='1080',
            username='user',
            password='pass'
        )
        
        result = await self.validator.validate_single_proxy(proxy)
        self.assertFalse(result)
    
    def test_validate_single_proxy_socks5_failure(self):
        asyncio.run(self.async_test_validate_single_proxy_socks5_failure())
    
    @patch('src.proxy_validator.ProxyValidator.test_http_connectivity')
    async def async_test_validate_single_proxy_http_success(self, mock_test):
        # Configure mock
        mock_test.return_value = True
        
        proxy = ProxyData(
            proxy_type='http',
            server='3.3.3.3',
            port='8080'
        )
        
        result = await self.validator.validate_single_proxy(proxy)
        self.assertTrue(result)
    
    def test_validate_single_proxy_http_success(self):
        asyncio.run(self.async_test_validate_single_proxy_http_success())
    
    @patch('src.proxy_validator.ProxyValidator.test_http_connectivity')
    async def async_test_validate_single_proxy_http_failure(self, mock_test):
        # Configure mock
        mock_test.side_effect = Exception("Connection failed")
        
        proxy = ProxyData(
            proxy_type='http',
            server='3.3.3.3',
            port='8080'
        )
        
        result = await self.validator.validate_single_proxy(proxy)
        self.assertFalse(result)
    
    def test_validate_single_proxy_http_failure(self):
        asyncio.run(self.async_test_validate_single_proxy_http_failure())
    
    @patch('src.proxy_validator.ProxyValidator.create_connection_test')
    async def async_test_test_mtproto_connectivity_success(self, mock_connection):
        # Configure mock
        mock_connection.return_value = True
        
        proxy = ProxyData(
            proxy_type='mtproto',
            server='1.1.1.1',
            port='443',
            secret='abcdef123456'
        )
        
        result = await self.validator.test_mtproto_connectivity(proxy)
        self.assertTrue(result)
        mock_connection.assert_called()
    
    def test_test_mtproto_connectivity_success(self):
        asyncio.run(self.async_test_test_mtproto_connectivity_success())
    
    @patch('src.proxy_validator.ProxyValidator.create_connection_test')
    async def async_test_test_mtproto_connectivity_failure(self, mock_connection):
        # Configure mock
        mock_connection.return_value = False
        
        proxy = ProxyData(
            proxy_type='mtproto',
            server='1.1.1.1',
            port='443',
            secret='abcdef123456'
        )
        
        result = await self.validator.test_mtproto_connectivity(proxy)
        self.assertFalse(result)
    
    def test_test_mtproto_connectivity_failure(self):
        asyncio.run(self.async_test_test_mtproto_connectivity_failure())
    
    @patch('aiohttp.ClientSession')
    async def async_test_test_socks5_connectivity_success(self, mock_session):
        # Setup mock session
        session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = session_instance
        
        # Mock successful connection
        mock_response = MagicMock()
        mock_response.status = 200
        session_instance.get.return_value.__aenter__.return_value = mock_response
        
        proxy = ProxyData(
            proxy_type='socks5',
            server='2.2.2.2',
            port='1080',
            username='user',
            password='pass'
        )
        
        result = await self.validator.test_socks5_connectivity(proxy)
        self.assertTrue(result)
    
    def test_test_socks5_connectivity_success(self):
        asyncio.run(self.async_test_test_socks5_connectivity_success())
    
    @patch('aiohttp.ClientSession')
    @patch('src.proxy_validator.ProxyValidator.create_connection_test')
    async def async_test_test_socks5_connectivity_fallback(self, mock_connection, mock_session):
        # Setup mock session
        session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = session_instance
        
        # Mock failed http connection but successful basic connection
        session_instance.get.side_effect = Exception("HTTP error")
        mock_connection.return_value = True
        
        proxy = ProxyData(
            proxy_type='socks5',
            server='2.2.2.2',
            port='1080',
            username='user',
            password='pass'
        )
        
        result = await self.validator.test_socks5_connectivity(proxy)
        self.assertTrue(result)
        mock_connection.assert_called_once()
    
    def test_test_socks5_connectivity_fallback(self):
        asyncio.run(self.async_test_test_socks5_connectivity_fallback())
    
    @patch('aiohttp.ClientSession')
    async def async_test_test_http_connectivity_success(self, mock_session):
        # Setup mock session
        session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = session_instance
        
        # Mock successful connection
        mock_response = MagicMock()
        mock_response.status = 200
        session_instance.get.return_value.__aenter__.return_value = mock_response
        
        proxy = ProxyData(
            proxy_type='http',
            server='3.3.3.3',
            port='8080'
        )
        
        result = await self.validator.test_http_connectivity(proxy)
        self.assertTrue(result)
    
    def test_test_http_connectivity_success(self):
        asyncio.run(self.async_test_test_http_connectivity_success())
    
    @patch('aiohttp.ClientSession')
    @patch('src.proxy_validator.ProxyValidator.create_connection_test')
    async def async_test_test_http_connectivity_fallback(self, mock_connection, mock_session):
        # Setup mock session
        session_instance = MagicMock()
        mock_session.return_value.__aenter__.return_value = session_instance
        
        # Mock failed http connection but successful basic connection
        session_instance.get.side_effect = Exception("HTTP error")
        mock_connection.return_value = True
        
        proxy = ProxyData(
            proxy_type='http',
            server='3.3.3.3',
            port='8080'
        )
        
        result = await self.validator.test_http_connectivity(proxy)
        self.assertTrue(result)
        mock_connection.assert_called_once()
    
    def test_test_http_connectivity_fallback(self):
        asyncio.run(self.async_test_test_http_connectivity_fallback())
    
    async def async_test_create_connection_test_success(self):
        # Mock asyncio.open_connection and wait_closed
        reader = MagicMock()
        writer = MagicMock()
        writer.wait_closed = AsyncMock()
        
        with patch('asyncio.open_connection', new=AsyncMock(return_value=(reader, writer))):
            with patch('asyncio.wait_for', new=AsyncMock(return_value=(reader, writer))):
                result = await self.validator.create_connection_test("example.com", 80)
                self.assertTrue(result)
    
    def test_create_connection_test_success(self):
        asyncio.run(self.async_test_create_connection_test_success())
    
    async def async_test_create_connection_test_timeout(self):
        # Mock timeout
        with patch('asyncio.open_connection', new=AsyncMock()):
            with patch('asyncio.wait_for', new=AsyncMock(side_effect=asyncio.TimeoutError())):
                result = await self.validator.create_connection_test("example.com", 80)
                self.assertFalse(result)
    
    def test_create_connection_test_timeout(self):
        asyncio.run(self.async_test_create_connection_test_timeout())
    
    def test_get_validation_status(self):
        # Setup test data
        proxy = ProxyData(proxy_type='http', server='1.1.1.1', port='80')
        self.validator.validation_results = {'1.1.1.1:80': True}
        
        # Test
        result = self.validator.get_validation_status(proxy)
        self.assertTrue(result)
        
        # Test for non-existent proxy
        proxy2 = ProxyData(proxy_type='http', server='2.2.2.2', port='80')
        result2 = self.validator.get_validation_status(proxy2)
        self.assertIsNone(result2)
    
    def test_filter_working_proxies(self):
        # Setup test data
        proxy1 = ProxyData(proxy_type='http', server='1.1.1.1', port='80')
        proxy2 = ProxyData(proxy_type='socks5', server='2.2.2.2', port='1080')
        proxy3 = ProxyData(proxy_type='mtproto', server='3.3.3.3', port='443')
        
        self.validator.validation_results = {
            '1.1.1.1:80': True,
            '2.2.2.2:1080': False,
            '3.3.3.3:443': True
        }
        
        # Test
        proxies = [proxy1, proxy2, proxy3]
        result = self.validator.filter_working_proxies(proxies)
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].server, '1.1.1.1')
        self.assertEqual(result[1].server, '3.3.3.3')
    
    def test_get_validation_summary(self):
        # Setup test data
        self.validator.validation_results = {
            '1.1.1.1:80': True,
            '2.2.2.2:1080': False,
            '3.3.3.3:443': True,
            '4.4.4.4:8080': False
        }
        
        # Test
        summary = self.validator.get_validation_summary()
        
        self.assertEqual(summary['total_tested'], 4)
        self.assertEqual(summary['working'], 2)
        self.assertEqual(summary['failed'], 2)
        self.assertEqual(summary['success_rate'], 50.0)
    
    def test_get_validation_summary_empty(self):
        # Setup empty data
        self.validator.validation_results = {}
        
        # Test
        summary = self.validator.get_validation_summary()
        
        self.assertEqual(summary['total_tested'], 0)
        self.assertEqual(summary['working'], 0)
        self.assertEqual(summary['failed'], 0)
        self.assertEqual(summary['success_rate'], 0)
    
    async def async_test_validate_single_proxy_unknown_type(self):
        # Test with unknown proxy type
        proxy = ProxyData(
            proxy_type='unknown',
            server='4.4.4.4',
            port='9999'
        )
        
        result = await self.validator.validate_single_proxy(proxy)
        self.assertFalse(result)
    
    def test_validate_single_proxy_unknown_type(self):
        asyncio.run(self.async_test_validate_single_proxy_unknown_type())


if __name__ == '__main__':
    unittest.main() 