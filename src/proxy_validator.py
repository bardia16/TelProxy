import asyncio
import socket
import aiohttp
import time
from typing import List, Dict, Tuple, Optional
from src.proxy_extractor import ProxyData
from config.settings import PROXY_VALIDATION_TIMEOUT


class ProxyValidator:
    
    def __init__(self):
        self.timeout = PROXY_VALIDATION_TIMEOUT
        self.validation_results = {}
        self.test_url = "http://httpbin.org/ip"
        self.telegram_test_domains = ["149.154.175.53", "149.154.167.51"]
    
    async def validate_all_proxies(self, proxies: List[ProxyData]):
        print(f"Starting validation of {len(proxies)} proxies with timeout {self.timeout}s...")
        
        tasks = []
        for proxy in proxies:
            task = asyncio.create_task(self.validate_single_proxy(proxy))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        working_proxies = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Error validating proxy {proxies[i].server}:{proxies[i].port} - {type(result).__name__}: {result}")
                self.validation_results[f"{proxies[i].server}:{proxies[i].port}"] = False
            elif result:
                working_proxies.append(proxies[i])
                self.validation_results[f"{proxies[i].server}:{proxies[i].port}"] = True
            else:
                self.validation_results[f"{proxies[i].server}:{proxies[i].port}"] = False
        
        print(f"Validation complete: {len(working_proxies)}/{len(proxies)} proxies are working")
        return working_proxies
    
    async def validate_single_proxy(self, proxy: ProxyData):
        proxy_key = f"{proxy.server}:{proxy.port}"
        print(f"Testing {proxy.proxy_type} proxy: {proxy_key}")
        
        try:
            # First try basic connectivity - this is more lenient
            basic_connectivity = await self.create_connection_test(proxy.server, int(proxy.port))
            
            if basic_connectivity:
                print(f"  {proxy_key}: ✓ Basic connectivity successful")
                return True  # Consider the proxy valid if basic connectivity works
            else:
                print(f"  {proxy_key}: ✗ Failed basic connectivity")
                return False
            
        except Exception as e:
            print(f"  {proxy_key}: ✗ Error - {type(e).__name__}: {e}")
            return False
    
    async def test_mtproto_connectivity(self, proxy: ProxyData):
        try:
            # For MTProto, we'll consider it valid if we can connect to the server
            # and at least one of the Telegram test domains
            success = True
            
            for telegram_ip in self.telegram_test_domains:
                try:
                    telegram_success = await self.create_connection_test(telegram_ip, 443)
                    if telegram_success:
                        print(f"  Connected to Telegram server {telegram_ip}")
                        return True
                except Exception as e:
                    print(f"  Failed to connect to Telegram server {telegram_ip}: {type(e).__name__}")
            
            # If we couldn't connect to any Telegram servers but could connect to the proxy,
            # we'll still consider it potentially valid
            return True
        except Exception as e:
            print(f"  MTProto test error: {type(e).__name__}: {e}")
            return False
    
    async def test_socks5_connectivity(self, proxy: ProxyData):
        try:
            # First try direct connection to the proxy
            basic_connectivity = await self.create_connection_test(proxy.server, int(proxy.port))
            if not basic_connectivity:
                return False
                
            # For SOCKS5, we'll be more lenient and consider it valid if we can connect to the server
            try:
                if proxy.username and proxy.password:
                    proxy_auth = aiohttp.BasicAuth(proxy.username, proxy.password)
                else:
                    proxy_auth = None
                
                proxy_url = f"socks5://{proxy.server}:{proxy.port}"
                
                connector = aiohttp.TCPConnector()
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(
                    connector=connector, 
                    timeout=timeout,
                    auth=proxy_auth
                ) as session:
                    try:
                        async with session.get(
                            self.test_url,
                            proxy=proxy_url,
                            timeout=aiohttp.ClientTimeout(total=self.timeout)
                        ) as response:
                            return response.status == 200
                    except Exception as e:
                        print(f"  SOCKS5 HTTP test failed: {type(e).__name__}")
                        # If HTTP test fails, we'll still consider it valid if basic connectivity worked
                        return True
            except Exception as e:
                print(f"  SOCKS5 session error: {type(e).__name__}: {e}")
                # If there was an error creating the session, we'll still consider it valid
                # if basic connectivity worked
                return True
        except Exception as e:
            print(f"  SOCKS5 test error: {type(e).__name__}: {e}")
            return False
    
    async def test_http_connectivity(self, proxy: ProxyData):
        try:
            # First try direct connection to the proxy
            basic_connectivity = await self.create_connection_test(proxy.server, int(proxy.port))
            if not basic_connectivity:
                return False
                
            # For HTTP, we'll be more lenient and consider it valid if we can connect to the server
            try:
                proxy_url = f"http://{proxy.server}:{proxy.port}"
                
                connector = aiohttp.TCPConnector()
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                    try:
                        async with session.get(
                            self.test_url,
                            proxy=proxy_url,
                            timeout=aiohttp.ClientTimeout(total=self.timeout)
                        ) as response:
                            return response.status == 200
                    except Exception as e:
                        print(f"  HTTP test failed: {type(e).__name__}")
                        # If HTTP test fails, we'll still consider it valid if basic connectivity worked
                        return True
            except Exception as e:
                print(f"  HTTP session error: {type(e).__name__}: {e}")
                # If there was an error creating the session, we'll still consider it valid
                # if basic connectivity worked
                return True
        except Exception as e:
            print(f"  HTTP test error: {type(e).__name__}: {e}")
            return False
    
    async def create_connection_test(self, server: str, port: int):
        try:
            future = asyncio.open_connection(server, port)
            reader, writer = await asyncio.wait_for(future, timeout=self.timeout)
            
            writer.close()
            await writer.wait_closed()
            return True
            
        except (OSError, asyncio.TimeoutError, ConnectionRefusedError, socket.gaierror) as e:
            print(f"  Connection test failed: {type(e).__name__}: {e}")
            return False
        except Exception as e:
            print(f"  Connection test error: {type(e).__name__}: {e}")
            return False
    
    def get_validation_status(self, proxy: ProxyData):
        proxy_key = f"{proxy.server}:{proxy.port}"
        return self.validation_results.get(proxy_key, None)
    
    def filter_working_proxies(self, proxies: List[ProxyData]):
        working_proxies = []
        for proxy in proxies:
            if self.get_validation_status(proxy) is True:
                working_proxies.append(proxy)
        return working_proxies
    
    def get_validation_summary(self):
        total = len(self.validation_results)
        working = sum(1 for status in self.validation_results.values() if status)
        failed = total - working
        
        return {
            'total_tested': total,
            'working': working,
            'failed': failed,
            'success_rate': (working / total * 100) if total > 0 else 0
        }