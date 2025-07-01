import re
import urllib.parse
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ProxyData:
    proxy_type: str
    server: str
    port: str
    secret: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    original_url: str = ""


class ProxyExtractor:
    
    def __init__(self):
        self.mtproto_patterns = []
        self.socks5_patterns = []
        self.http_patterns = []
        self._initialize_patterns()
    
    def _initialize_patterns(self):
        # MTProto patterns
        self.mtproto_patterns = [
            r'tg://proxy\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)[^&\s]*secret=([^&\s]+)',
            r'https?://t\.me/proxy\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)[^&\s]*secret=([^&\s]+)',
            r'tg://proxy\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)',
            r'https?://t\.me/proxy\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)',
            # Add more lenient pattern for raw server:port format
            r'(?:proxy|mtproto)\s*(?:server|address)?:?\s*([a-zA-Z0-9\.\-]+)[:\s]+(\d{2,5})'
        ]
        
        # SOCKS5 patterns
        self.socks5_patterns = [
            r'tg://socks\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)[^&\s]*user=([^&\s]+)[^&\s]*pass=([^&\s]+)',
            r'https?://t\.me/socks\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)[^&\s]*user=([^&\s]+)[^&\s]*pass=([^&\s]+)',
            r'tg://socks\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)',
            r'https?://t\.me/socks\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)',
            # Add more lenient pattern for raw server:port format
            r'(?:socks5|socks)\s*(?:server|address)?:?\s*([a-zA-Z0-9\.\-]+)[:\s]+(\d{2,5})'
        ]
        
        # HTTP patterns
        self.http_patterns = [
            r'tg://http\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)',
            r'https?://t\.me/http\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)',
            # Add more lenient pattern for raw server:port format
            r'(?:http)\s*(?:server|address)?:?\s*([a-zA-Z0-9\.\-]+)[:\s]+(\d{2,5})'
        ]
        
        # Generic IP:port pattern (will be classified as mtproto by default)
        self.generic_ip_port_pattern = r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{2,5})'
    
    def extract_all_proxies(self, text: str):
        if not text:
            return []
        
        all_proxies = []
        
        # Extract from specific patterns
        all_proxies.extend(self.extract_mtproto_proxies(text))
        all_proxies.extend(self.extract_socks5_proxies(text))
        all_proxies.extend(self.extract_http_proxies(text))
        
        # Extract from generic IP:port pattern
        generic_matches = re.finditer(self.generic_ip_port_pattern, text, re.IGNORECASE)
        for match in generic_matches:
            server = match.group(1)
            port = match.group(2)
            full_url = f"{server}:{port}"
            
            # Check if this IP:port is already extracted
            if not any(p.server == server and p.port == port for p in all_proxies):
                proxy = ProxyData(
                    proxy_type='mtproto',  # Default to mtproto
                    server=server,
                    port=port,
                    original_url=full_url
                )
                all_proxies.append(proxy)
        
        print(f"Found {len(all_proxies)} potential proxies in text")
        
        validated_proxies = []
        for proxy in all_proxies:
            if self.validate_proxy_format(proxy):
                validated_proxies.append(proxy)
            else:
                print(f"Invalid proxy format: {proxy.server}:{proxy.port} ({proxy.proxy_type})")
        
        print(f"Validated {len(validated_proxies)} proxies with correct format")
        return validated_proxies
    
    def extract_mtproto_proxies(self, text: str):
        proxies = []
        
        for pattern in self.mtproto_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                full_url = match.group(0)
                parsed_proxy = self.parse_mtproto_url(full_url)
                if parsed_proxy:
                    proxies.append(parsed_proxy)
        
        return proxies
    
    def extract_socks5_proxies(self, text: str):
        proxies = []
        
        for pattern in self.socks5_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                full_url = match.group(0)
                parsed_proxy = self.parse_socks5_url(full_url)
                if parsed_proxy:
                    proxies.append(parsed_proxy)
        
        return proxies
    
    def extract_http_proxies(self, text: str):
        proxies = []
        
        for pattern in self.http_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                full_url = match.group(0)
                parsed_proxy = self.parse_http_url(full_url)
                if parsed_proxy:
                    proxies.append(parsed_proxy)
        
        return proxies
    
    def parse_mtproto_url(self, url: str):
        try:
            # Handle URL format
            if url.startswith('tg://') or url.startswith('http'):
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                
                server = params.get('server', [None])[0]
                port = params.get('port', [None])[0]
                secret = params.get('secret', [None])[0]
            # Handle raw server:port format
            elif ':' in url:
                match = re.search(r'([a-zA-Z0-9\.\-]+)[:\s]+(\d{2,5})', url)
                if match:
                    server = match.group(1)
                    port = match.group(2)
                    secret = None
                else:
                    return None
            else:
                return None
            
            if not server or not port:
                return None
            
            return ProxyData(
                proxy_type='mtproto',
                server=server,
                port=port,
                secret=secret,
                original_url=url
            )
        except Exception as e:
            print(f"Error parsing MTProto URL '{url}': {type(e).__name__}: {e}")
            return None
    
    def parse_socks5_url(self, url: str):
        try:
            # Handle URL format
            if url.startswith('tg://') or url.startswith('http'):
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                
                server = params.get('server', [None])[0]
                port = params.get('port', [None])[0]
                username = params.get('user', [None])[0]
                password = params.get('pass', [None])[0]
            # Handle raw server:port format
            elif ':' in url:
                match = re.search(r'([a-zA-Z0-9\.\-]+)[:\s]+(\d{2,5})', url)
                if match:
                    server = match.group(1)
                    port = match.group(2)
                    username = None
                    password = None
                else:
                    return None
            else:
                return None
            
            if not server or not port:
                return None
            
            return ProxyData(
                proxy_type='socks5',
                server=server,
                port=port,
                username=username,
                password=password,
                original_url=url
            )
        except Exception as e:
            print(f"Error parsing SOCKS5 URL '{url}': {type(e).__name__}: {e}")
            return None
    
    def parse_http_url(self, url: str):
        try:
            # Handle URL format
            if url.startswith('tg://') or url.startswith('http'):
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                
                server = params.get('server', [None])[0]
                port = params.get('port', [None])[0]
            # Handle raw server:port format
            elif ':' in url:
                match = re.search(r'([a-zA-Z0-9\.\-]+)[:\s]+(\d{2,5})', url)
                if match:
                    server = match.group(1)
                    port = match.group(2)
                else:
                    return None
            else:
                return None
            
            if not server or not port:
                return None
            
            return ProxyData(
                proxy_type='http',
                server=server,
                port=port,
                original_url=url
            )
        except Exception as e:
            print(f"Error parsing HTTP URL '{url}': {type(e).__name__}: {e}")
            return None
    
    def validate_proxy_format(self, proxy_data: ProxyData):
        if not proxy_data or not proxy_data.server or not proxy_data.port:
            return False
        
        # Be more lenient with IP/domain validation
        if not self._is_valid_ip_or_domain(proxy_data.server):
            print(f"Invalid server address: {proxy_data.server}")
            return False
        
        try:
            port_num = int(proxy_data.port)
            if port_num < 1 or port_num > 65535:
                print(f"Invalid port number: {proxy_data.port}")
                return False
        except ValueError:
            print(f"Port is not a number: {proxy_data.port}")
            return False
        
        if proxy_data.proxy_type == 'mtproto':
            if proxy_data.secret and not self._is_valid_hex_secret(proxy_data.secret):
                print(f"Invalid MTProto secret: {proxy_data.secret}")
                return False
        
        return True
    
    def _is_valid_ip_or_domain(self, address: str):
        # More lenient IP validation
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        # More lenient domain validation
        domain_pattern = r'^[a-zA-Z0-9\-\.]+$'
        
        if re.match(ip_pattern, address):
            parts = address.split('.')
            # Be lenient with IP validation - just check basic format
            return len(parts) == 4 and all(part.isdigit() for part in parts)
        
        return bool(re.match(domain_pattern, address))
    
    def _is_valid_hex_secret(self, secret: str):
        # Be more lenient with secret validation
        return bool(re.match(r'^[a-fA-F0-9]+$', secret)) 