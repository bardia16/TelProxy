"""
Message formatter for proxy results.
Creates formatted messages for real-time and streaming proxies.
"""

from typing import List, Tuple
from src.proxy_extractor import ProxyData
from src.proxy_classifier import ProxyPerformance

class MessageFormatter:
    def __init__(self):
        self.bar_length = 10  # Length of the speed indicator bar
        self.bar_fill = '■'   # Character for filled portion
        self.bar_empty = '□'  # Character for empty portion
    
    def format_realtime_message(self, proxies: List[Tuple[ProxyData, ProxyPerformance]]) -> str:
        """Format real-time proxies message with latencies."""
        if not proxies:
            return "No real-time proxies available"
            
        # Sort by latency
        sorted_proxies = sorted(proxies, key=lambda x: x[1].latency)
        
        # Format header
        lines = [
            f"🚀 Real-time Proxies • {len(proxies)} total • ⚡ By ping\n"
        ]
        
        # Group latencies into lines of 6 for readability
        latencies = []
        for _, perf in sorted_proxies:
            latency_ms = int(perf.latency * 1000)  # Convert to milliseconds
            latencies.append(f"{latency_ms}ms")
        
        # Split into groups of 6
        for i in range(0, len(latencies), 6):
            group = latencies[i:i+6]
            lines.append(" • ".join(group))
        
        # Add footer
        lines.append("\n🔄 Hourly updates")
        
        return "\n".join(lines)
    
    def format_streaming_message(self, proxies: List[Tuple[ProxyData, ProxyPerformance]]) -> str:
        """Format streaming proxies message with speed bars."""
        if not proxies:
            return "No streaming proxies available"
            
        # Sort by speed (using max of download/upload)
        sorted_proxies = sorted(
            proxies,
            key=lambda x: max(x[1].download_speed, x[1].upload_speed),
            reverse=True
        )
        
        # Format header
        lines = [
            f"📥 Streaming Proxies • {len(proxies)} total • 💫 By speed\n"
        ]
        
        # Get the highest speed for percentage calculations
        max_speed = max(max(p[1].download_speed, p[1].upload_speed) for p in sorted_proxies)
        
        # Format each proxy's speed bar
        for _, perf in sorted_proxies:
            speed = max(perf.download_speed, perf.upload_speed)
            speed_mbps = speed / (1024 * 1024)  # Convert to MB/s
            
            # Calculate filled bar portions
            fill_count = int(round((speed / max_speed) * self.bar_length))
            empty_count = self.bar_length - fill_count
            
            # Create the bar
            bar = self.bar_fill * fill_count + self.bar_empty * empty_count
            
            # Format the line with proper alignment
            lines.append(f"{speed_mbps:4.1f} MB/s {bar}")
        
        # Add footer
        lines.append("\n🔄 Hourly updates")
        
        return "\n".join(lines)
    
    def format_speed(self, bytes_per_sec: float) -> str:
        """Format speed in bytes/second to MB/s string."""
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s" 