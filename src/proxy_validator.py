import asyncio
import aiohttp
from typing import List, Dict
from src.proxy_extractor import ProxyData
from config.settings import PROXY_VALIDATION_TIMEOUT, PING_MEASUREMENTS, PING_DELAY


class ProxyValidator:
    
    def __init__(self):
        self.timeout = PROXY_VALIDATION_TIMEOUT
        self.validation_results = {}
        self.ping_results = {}
        self.ping_measurements = PING_MEASUREMENTS
        self.ping_delay = PING_DELAY
        self.validation_api_url = "http://127.0.0.1:9100/validate"
    
    async def validate_all_proxies(self, proxies: List[ProxyData]):
        print(f"Starting validation of {len(proxies)} proxies with timeout {self.timeout}s...")
        
        tasks = []
        for proxy in proxies:
            task = asyncio.create_task(self.validate_single_proxy(proxy))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        working_proxies = []
        for i, result in enumerate(results):
            proxy_key = f"{proxies[i].server}:{proxies[i].port}"
            if isinstance(result, Exception):
                print(f"Error validating proxy {proxy_key} - {type(result).__name__}: {result}")
                self.validation_results[proxy_key] = False
                self.ping_results[proxy_key] = float('inf')
            elif result:
                working_proxies.append(proxies[i])
                self.validation_results[proxy_key] = True
            else:
                self.validation_results[proxy_key] = False
                self.ping_results[proxy_key] = float('inf')
        
        # Sort working proxies by ping (lowest ping first)
        working_proxies.sort(key=lambda proxy: self.get_proxy_ping(proxy))
        
        print(f"Validation complete: {len(working_proxies)}/{len(proxies)} proxies are working")
        print("🏆 Top 10 proxies by ping:")
        for i, proxy in enumerate(working_proxies[:10]):
            ping = self.get_proxy_ping(proxy)
            if ping != float('inf'):
                ping_str = f"{ping*1000:.0f}ms"
            else:
                ping_str = "N/A"
            print(f"  {i+1:2d}. {proxy.server:<20} {proxy.port:<6} - {ping_str} ({proxy.proxy_type})")
        
        return working_proxies
    
    async def validate_single_proxy(self, proxy: ProxyData):
        proxy_key = f"{proxy.server}:{proxy.port}"
        
        try:
            # Validate and measure ping using remote service
            async with aiohttp.ClientSession() as session:
                payload = {
                    "proxy": f"{proxy.server}:{proxy.port}",
                    "proxy_type": proxy.proxy_type,
                    "username": proxy.username if hasattr(proxy, 'username') else None,
                    "password": proxy.password if hasattr(proxy, 'password') else None,
                    "ping_count": self.ping_measurements,
                    "ping_delay": self.ping_delay
                }
                
                async with session.post(
                    self.validation_api_url,
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Store ping result and handle telegram connectivity for MTProto
                        self.ping_results[proxy_key] = result.get("ping", float('inf'))
                        if proxy.proxy_type == "mtproto":
                            return result.get("telegram_connectivity", False)
                        return result.get("valid", False)
                    return False
            
        except Exception as e:
            print(f"  {proxy_key}: ✗ Error - {type(e).__name__}: {e}")
            self.ping_results[proxy_key] = float('inf')
            return False
    
    def get_validation_status(self, proxy: ProxyData):
        return self.validation_results.get(f"{proxy.server}:{proxy.port}", False)
    
    def filter_working_proxies(self, proxies: List[ProxyData]):
        return [p for p in proxies if self.get_validation_status(p)]
    
    def get_proxy_ping(self, proxy: ProxyData):
        return self.ping_results.get(f"{proxy.server}:{proxy.port}", float('inf'))
    
    def get_sorted_proxies_by_ping(self, proxies: List[ProxyData]):
        return sorted(proxies, key=lambda p: self.get_proxy_ping(p))
    
    def configure_ping_settings(self, measurements: int = 5, delay: float = 0.2):
        self.ping_measurements = measurements
        self.ping_delay = delay