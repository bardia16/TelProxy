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
        self.batch_size = 50
        self.batch_delay = 1
        self.max_retries = 2
    
    async def validate_all_proxies(self, proxies: List[ProxyData]):
        print(f"Starting validation of {len(proxies)} proxies with timeout {self.timeout}s...")
        print(f"Processing in batches of {self.batch_size} with {self.batch_delay}s delay between batches")
        
        working_proxies = []
        
        # Process proxies in batches
        for i in range(0, len(proxies), self.batch_size):
            batch = proxies[i:i + self.batch_size]
            print(f"\nValidating batch {(i//self.batch_size)+1}/{(len(proxies)-1)//self.batch_size + 1} ({len(batch)} proxies)")
            
            tasks = []
            for proxy in batch:
                task = asyncio.create_task(self.validate_single_proxy_with_retry(proxy))
                tasks.append(task)
            
            # Wait for the current batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results for this batch
            for j, result in enumerate(results):
                proxy = batch[j]
                proxy_key = f"{proxy.server}:{proxy.port}"
                
                if isinstance(result, Exception):
                    print(f"  {proxy_key}: ✗ Error - {type(result).__name__}: {result}")
                    self.validation_results[proxy_key] = False
                    self.ping_results[proxy_key] = None
                elif result:
                    working_proxies.append(proxy)
                    self.validation_results[proxy_key] = True
                    print(f"  {proxy_key}: ✓ Working")
                else:
                    self.validation_results[proxy_key] = False
                    self.ping_results[proxy_key] = None
                    print(f"  {proxy_key}: ✗ Failed validation")
            
            # Wait before processing the next batch
            if i + self.batch_size < len(proxies):
                print(f"Waiting {self.batch_delay}s before next batch...")
                await asyncio.sleep(self.batch_delay)
        
        # Sort working proxies by ping (lowest ping first), handling None values
        working_proxies.sort(key=lambda proxy: self.get_proxy_ping(proxy))
        
        print(f"\nValidation complete: {len(working_proxies)}/{len(proxies)} proxies are working")
        if working_proxies:
            print("\n🏆 Top 10 proxies by ping:")
            for i, proxy in enumerate(working_proxies[:10]):
                ping = self.get_proxy_ping(proxy)
                if ping != float('inf'):
                    ping_str = f"{ping*1000:.0f}ms"
                else:
                    ping_str = "N/A"
                print(f"  {i+1:2d}. {proxy.server:<20} {proxy.port:<6} - {ping_str} ({proxy.proxy_type})")
        
        return working_proxies
    
    async def validate_single_proxy_with_retry(self, proxy: ProxyData, attempt: int = 0) -> bool:
        try:
            return await self.validate_single_proxy(proxy)
        except Exception as e:
            if attempt < self.max_retries:
                print(f"  Retrying {proxy.server}:{proxy.port} (attempt {attempt + 2}/{self.max_retries + 1})")
                await asyncio.sleep(1)  # Wait before retry
                return await self.validate_single_proxy_with_retry(proxy, attempt + 1)
            raise e
    
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
        """Get the ping time for a proxy. Returns float('inf') if no ping data or failed ping."""
        ping = self.ping_results.get(f"{proxy.server}:{proxy.port}")
        return float('inf') if ping is None else ping
    
    def get_sorted_proxies_by_ping(self, proxies: List[ProxyData]):
        """Sort proxies by ping time, handling None values."""
        return sorted(proxies, key=lambda p: self.get_proxy_ping(p))
    
    def configure_ping_settings(self, measurements: int = 5, delay: float = 0.2):
        self.ping_measurements = measurements
        self.ping_delay = delay
        
    def configure_batch_settings(self, batch_size: int = 5, batch_delay: float = 2):
        """Configure batch processing settings
        
        Args:
            batch_size: Number of proxies to validate concurrently
            batch_delay: Delay in seconds between batches
        """
        self.batch_size = batch_size
        self.batch_delay = batch_delay