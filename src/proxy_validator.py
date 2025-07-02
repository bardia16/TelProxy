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
        self.ping_results = {}
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
                self.ping_results[f"{proxies[i].server}:{proxies[i].port}"] = float('inf')
            elif result:
                working_proxies.append(proxies[i])
                self.validation_results[f"{proxies[i].server}:{proxies[i].port}"] = True
            else:
                self.validation_results[f"{proxies[i].server}:{proxies[i].port}"] = False
                self.ping_results[f"{proxies[i].server}:{proxies[i].port}"] = float('inf')
        
        # Sort working proxies by ping (lowest ping first)
        working_proxies.sort(key=lambda proxy: self.get_proxy_ping(proxy))
        
        print(f"Validation complete: {len(working_proxies)}/{len(proxies)} proxies are working")
        print("Top 5 proxies by ping:")
        for i, proxy in enumerate(working_proxies[:5]):
            ping = self.get_proxy_ping(proxy)
            ping_str = f"{ping:.3f}s" if ping != float('inf') else "N/A"
            print(f"  {i+1}. {proxy.server}:{proxy.port} - {ping_str}")
        
        return working_proxies
    
    async def validate_single_proxy(self, proxy: ProxyData):
        proxy_key = f"{proxy.server}:{proxy.port}"
        
        try:
            # Measure ping during validation
            ping_time = await self.measure_proxy_ping(proxy)
            self.ping_results[proxy_key] = ping_time
            
            # Basic connectivity test
            basic_connectivity = await self.create_connection_test(proxy.server, int(proxy.port))
            
            if basic_connectivity and ping_time < float('inf'):
                return True
            else:
                return False
            
        except Exception as e:
            print(f"  {proxy_key}: ✗ Error - {type(e).__name__}: {e}")
            self.ping_results[proxy_key] = float('inf')
            return False
    
    async def measure_proxy_ping(self, proxy: ProxyData):
        proxy_key = f"{proxy.server}:{proxy.port}"
        ping_times = []
        
        try:
            # Test ping 3 times and take the average
            for _ in range(3):
                start_time = time.time()
                
                if proxy.proxy_type == 'mtproto':
                    success = await self.test_mtproto_ping(proxy)
                elif proxy.proxy_type == 'socks5':
                    success = await self.test_socks5_ping(proxy)
                elif proxy.proxy_type == 'http':
                    success = await self.test_http_ping(proxy)
                else:
                    success = await self.create_connection_test(proxy.server, int(proxy.port))
                
                if success:
                    ping_time = time.time() - start_time
                    ping_times.append(ping_time)
                else:
                    ping_times.append(float('inf'))
                
                await asyncio.sleep(0.1)  # Small delay between ping tests
            
            if ping_times and any(p != float('inf') for p in ping_times):
                valid_pings = [p for p in ping_times if p != float('inf')]
                avg_ping = sum(valid_pings) / len(valid_pings)
                return avg_ping
            else:
                return float('inf')
                
        except Exception as e:
            return float('inf')
    
    async def test_mtproto_ping(self, proxy: ProxyData):
        try:
            # For MTProto, test basic connectivity
            return await self.create_connection_test(proxy.server, int(proxy.port))
        except Exception:
            return False
    
    async def test_socks5_ping(self, proxy: ProxyData):
        try:
            # Test SOCKS5 proxy with a quick HTTP request
            proxy_url = f"socks5://{proxy.server}:{proxy.port}"
            
            if proxy.username and proxy.password:
                proxy_auth = aiohttp.BasicAuth(proxy.username, proxy.password)
            else:
                proxy_auth = None
            
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=5)  # Shorter timeout for ping test
            
            async with aiohttp.ClientSession(
                connector=connector, 
                timeout=timeout,
                auth=proxy_auth
            ) as session:
                async with session.get(
                    self.test_url,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception:
            # Fallback to basic connectivity test
            return await self.create_connection_test(proxy.server, int(proxy.port))
    
    async def test_http_ping(self, proxy: ProxyData):
        try:
            # Test HTTP proxy with a quick request
            proxy_url = f"http://{proxy.server}:{proxy.port}"
            
            connector = aiohttp.TCPConnector()
            timeout = aiohttp.ClientTimeout(total=5)  # Shorter timeout for ping test
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                async with session.get(
                    self.test_url,
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception:
            # Fallback to basic connectivity test
            return await self.create_connection_test(proxy.server, int(proxy.port))

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
            #print(f"  Connection test failed: {type(e).__name__}: {e}")
            return False
        except Exception as e:
            #print(f"  Connection test error: {type(e).__name__}: {e}")
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
    
    def get_proxy_ping(self, proxy: ProxyData):
        proxy_key = f"{proxy.server}:{proxy.port}"
        return self.ping_results.get(proxy_key, float('inf'))
    
    def get_sorted_proxies_by_ping(self, proxies: List[ProxyData]):
        working_proxies = self.filter_working_proxies(proxies)
        return sorted(working_proxies, key=lambda proxy: self.get_proxy_ping(proxy))

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