"""
Proxy classifier that categorizes proxies into two equal groups:
- Real-time Proxies: Best performing proxies for real-time applications (chat, gaming)
- Streaming Proxies: Best performing proxies for high-bandwidth needs (streaming, downloads)
"""

import asyncio
import time
import aiohttp
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from src.proxy_extractor import ProxyData

@dataclass
class ProxyPerformance:
    download_speed: float  # bytes per second
    upload_speed: float    # bytes per second
    latency: float        # seconds
    category: str         # 'realtime' or 'streaming'
    timestamp: float      # unix timestamp
    measurements: int     # number of successful measurements

class ProxyClassifier:
    def __init__(self):
        # Test file sizes for bandwidth measurement
        self.test_sizes = [
            512 * 1024,    # 512KB for quick test
            1024 * 1024,   # 1MB for main test
            2 * 1024 * 1024  # 2MB for verification
        ]
        self.timeout = 10  # seconds
        self.retry_count = 2  # Number of retries for failed tests
        self.measurement_count = 3  # Number of measurements to average
        
        # Use reliable CDNs for testing
        self.download_test_urls = [
            "https://speed.cloudflare.com/__down",
            "https://speed.hetzner.de/1MB.bin",
            "https://speedtest.tele2.net/1MB.zip"
        ]
    
    async def classify_proxies(self, proxies: List[ProxyData]) -> Dict[str, List[Tuple[ProxyData, ProxyPerformance]]]:
        """
        Test and classify all proxies, splitting them into two equal groups.
        Returns dict with 'realtime' and 'streaming' lists of (proxy, performance) tuples.
        """
        results = []
        total = len(proxies)
        
        # Test all proxies with progress updates
        for i, proxy in enumerate(proxies, 1):
            print(f"\rTesting proxy {i}/{total}: {proxy.server}:{proxy.port}", end="")
            performance = await self._test_proxy(proxy)
            if performance:
                results.append((proxy, performance))
        print()  # New line after progress
        
        if not results:
            return {'realtime': [], 'streaming': []}
        
        # Sort all proxies by their performance metrics
        # For real-time: prioritize latency
        realtime_sorted = sorted(results, key=lambda x: x[1].latency)
        
        # For streaming: prioritize bandwidth
        streaming_sorted = sorted(
            results,
            key=lambda x: max(x[1].download_speed, x[1].upload_speed),
            reverse=True
        )
        
        # Split into two groups
        mid_point = len(results) // 2
        
        # Determine which proxies appear in the top half of both lists
        # and assign them based on where they rank better
        realtime_set = set(p[0] for p in realtime_sorted[:mid_point])
        streaming_set = set(p[0] for p in streaming_sorted[:mid_point])
        
        # Proxies that are in top half of both lists
        overlap = realtime_set.intersection(streaming_set)
        
        realtime_proxies = []
        streaming_proxies = []
        used_proxies = set()
        
        # First, assign overlapping proxies to their better-performing category
        for proxy, perf in results:
            if proxy in overlap and proxy not in used_proxies:
                # Get positions in both sorted lists
                realtime_pos = next(i for i, (p, _) in enumerate(realtime_sorted) if p == proxy)
                streaming_pos = next(i for i, (p, _) in enumerate(streaming_sorted) if p == proxy)
                
                # Assign to category where it ranks better
                if realtime_pos < streaming_pos:
                    perf.category = 'realtime'
                    realtime_proxies.append((proxy, perf))
                else:
                    perf.category = 'streaming'
                    streaming_proxies.append((proxy, perf))
                used_proxies.add(proxy)
        
        # Then fill remaining spots in each category
        for proxy, perf in results:
            if proxy not in used_proxies:
                if len(realtime_proxies) < mid_point:
                    perf.category = 'realtime'
                    realtime_proxies.append((proxy, perf))
                else:
                    perf.category = 'streaming'
                    streaming_proxies.append((proxy, perf))
                used_proxies.add(proxy)
        
        return {
            'realtime': realtime_proxies,
            'streaming': streaming_proxies
        }
    
    async def _test_proxy(self, proxy: ProxyData) -> Optional[ProxyPerformance]:
        """Test a single proxy's performance metrics with multiple measurements."""
        try:
            # First test latency as it's quicker
            latencies = []
            for _ in range(self.measurement_count):
                latency = await self._measure_latency(proxy)
                if latency != float('inf'):
                    latencies.append(latency)
                await asyncio.sleep(0.2)  # Small delay between tests
            
            if not latencies:
                return None
            
            avg_latency = sum(latencies) / len(latencies)
            
            # Then test bandwidth
            download_speeds = []
            upload_speeds = []
            
            # Multiple measurements with different file sizes
            for size in self.test_sizes:
                for _ in range(self.retry_count):
                    download_speed = await self._measure_download_speed(proxy, size)
                    if download_speed > 0:
                        download_speeds.append(download_speed)
                        break
                
                for _ in range(self.retry_count):
                    upload_speed = await self._measure_upload_speed(proxy, size)
                    if upload_speed > 0:
                        upload_speeds.append(upload_speed)
                        break
                
                await asyncio.sleep(0.2)  # Small delay between tests
            
            if not download_speeds and not upload_speeds:
                return None
            
            return ProxyPerformance(
                download_speed=max(download_speeds) if download_speeds else 0,
                upload_speed=max(upload_speeds) if upload_speeds else 0,
                latency=avg_latency,
                category='',  # Will be set during classification
                timestamp=time.time(),
                measurements=len(download_speeds) + len(upload_speeds)
            )
            
        except Exception as e:
            print(f"\nPerformance test failed for {proxy.server}:{proxy.port} - {str(e)}")
            return None
    
    async def _measure_latency(self, proxy: ProxyData) -> float:
        """Measure round-trip time to a test endpoint."""
        try:
            proxy_url = self._get_proxy_url(proxy)
            
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                async with session.get(
                    'https://api.ipify.org',  # Lightweight endpoint
                    proxy=proxy_url,
                    timeout=self.timeout
                ) as response:
                    if response.status != 200:
                        return float('inf')
                    
                return time.time() - start_time
                
        except Exception:
            return float('inf')
    
    async def _measure_download_speed(self, proxy: ProxyData, test_size: int) -> float:
        """Measure download speed using a test file of specified size."""
        try:
            proxy_url = self._get_proxy_url(proxy)
            best_speed = 0
            
            for endpoint in self.download_test_urls:
                try:
                    async with aiohttp.ClientSession() as session:
                        start_time = time.time()
                        
                        headers = {'Range': f'bytes=0-{test_size-1}'}
                        
                        async with session.get(
                            endpoint,
                            proxy=proxy_url,
                            timeout=self.timeout,
                            headers=headers
                        ) as response:
                            if response.status not in (200, 206):
                                continue
                            
                            bytes_received = 0
                            async for chunk in response.content.iter_chunked(8192):
                                bytes_received += len(chunk)
                                if bytes_received >= test_size:
                                    break
                            
                            duration = time.time() - start_time
                            if duration > 0 and bytes_received > 0:
                                speed = bytes_received / duration
                                best_speed = max(best_speed, speed)
                                
                except Exception:
                    continue
            
            return best_speed
            
        except Exception:
            return 0
    
    async def _measure_upload_speed(self, proxy: ProxyData, test_size: int) -> float:
        """Measure upload speed using test data of specified size."""
        try:
            proxy_url = self._get_proxy_url(proxy)
            
            # Generate test data
            data = b'0' * test_size
            
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                async with session.post(
                    'https://httpbin.org/post',
                    proxy=proxy_url,
                    timeout=self.timeout,
                    data=data
                ) as response:
                    if response.status != 200:
                        return 0
                    
                duration = time.time() - start_time
                return test_size / duration if duration > 0 else 0
                
        except Exception:
            return 0
    
    def _get_proxy_url(self, proxy: ProxyData) -> str:
        """Convert ProxyData to URL format for aiohttp."""
        if proxy.proxy_type == 'socks5':
            prefix = 'socks5://'
        elif proxy.proxy_type == 'http':
            prefix = 'http://'
        else:
            raise ValueError(f"Unsupported proxy type for testing: {proxy.proxy_type}")
            
        if proxy.username and proxy.password:
            auth = f"{proxy.username}:{proxy.password}@"
        else:
            auth = ""
            
        return f"{prefix}{auth}{proxy.server}:{proxy.port}"
    
    def format_speed(self, speed: float) -> str:
        """Format speed in bytes/second to human readable format."""
        if speed == 0:
            return "0 B/s"
            
        units = ['B/s', 'KB/s', 'MB/s', 'GB/s']
        unit_index = 0
        
        while speed >= 1024 and unit_index < len(units) - 1:
            speed /= 1024
            unit_index += 1
            
        return f"{speed:.2f} {units[unit_index]}" 