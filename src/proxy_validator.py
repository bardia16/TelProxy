import asyncio
import socket
import aiohttp
import time
from typing import List, Dict, Tuple, Optional
from src.proxy_extractor import ProxyData
from src.proxy_classifier import ProxyClassifier, ProxyPerformance
from src.message_formatter import MessageFormatter
from config.settings import PROXY_VALIDATION_TIMEOUT


class ProxyValidator:
    
    def __init__(self):
        self.timeout = PROXY_VALIDATION_TIMEOUT
        self.validation_results = {}
        self.classifier = ProxyClassifier()
        self.formatter = MessageFormatter()
    
    async def validate_all_proxies(self, proxies: List[ProxyData]) -> Tuple[str, str]:
        """
        Validate and classify proxies, returning formatted messages for both categories.
        Returns (realtime_message, streaming_message)
        """
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
        
        if not working_proxies:
            print("\nNo working proxies found!")
            return "No proxies available", "No proxies available"
        
        # Classify working proxies into two equal groups
        print(f"\nClassifying {len(working_proxies)} working proxies...")
        classified_proxies = await self.classifier.classify_proxies(working_proxies)
        
        # Format messages
        realtime_message = self.formatter.format_realtime_message(classified_proxies['realtime'])
        streaming_message = self.formatter.format_streaming_message(classified_proxies['streaming'])
        
        # Print summary
        print(f"\nValidation complete: {len(working_proxies)}/{len(proxies)} proxies are working")
        print(f"Split into {len(classified_proxies['realtime'])} real-time and {len(classified_proxies['streaming'])} streaming proxies")
        
        return realtime_message, streaming_message
    
    async def validate_single_proxy(self, proxy: ProxyData):
        """Basic connectivity test for the proxy."""
        try:
            # Test basic connectivity
            basic_connectivity = await self._test_basic_connectivity(proxy)
            return basic_connectivity
        except Exception as e:
            print(f"Validation failed for {proxy.server}:{proxy.port} - {str(e)}")
            return False
    
    async def _test_basic_connectivity(self, proxy: ProxyData):
        """Test if the proxy responds to basic connections."""
        try:
            proxy_url = self._get_proxy_url(proxy)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://api.ipify.org',  # Lightweight endpoint
                    proxy=proxy_url,
                    timeout=self.timeout
                ) as response:
                    return response.status == 200
        except Exception:
            return False
    
    def _get_proxy_url(self, proxy: ProxyData) -> str:
        """Convert ProxyData to URL format for aiohttp."""
        if proxy.proxy_type == 'socks5':
            prefix = 'socks5://'
        elif proxy.proxy_type == 'http':
            prefix = 'http://'
        else:
            raise ValueError(f"Unsupported proxy type: {proxy.proxy_type}")
            
        if proxy.username and proxy.password:
            auth = f"{proxy.username}:{proxy.password}@"
        else:
            auth = ""
            
        return f"{prefix}{auth}{proxy.server}:{proxy.port}"