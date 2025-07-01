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
        self.mtproto_patterns = [
            r'tg://proxy\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)[^&\s]*secret=([^&\s]+)',
            r'https?://t\.me/proxy\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)[^&\s]*secret=([^&\s]+)',
            r'tg://proxy\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)',
            r'https?://t\.me/proxy\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)'
        ]
        
        self.socks5_patterns = [
            r'tg://socks\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)[^&\s]*user=([^&\s]+)[^&\s]*pass=([^&\s]+)',
            r'https?://t\.me/socks\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)[^&\s]*user=([^&\s]+)[^&\s]*pass=([^&\s]+)',
            r'tg://socks\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)',
            r'https?://t\.me/socks\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)'
        ]
        
        self.http_patterns = [
            r'tg://http\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)',
            r'https?://t\.me/http\?[^&\s]*server=([^&\s]+)[^&\s]*port=([^&\s]+)'
        ]
    
    def extract_all_proxies(self, text: str):
        if not text:
            return []
        
        all_proxies = []
        
        all_proxies.extend(self.extract_mtproto_proxies(text))
        all_proxies.extend(self.extract_socks5_proxies(text))
        all_proxies.extend(self.extract_http_proxies(text))
        
        validated_proxies = []
        for proxy in all_proxies:
            if self.validate_proxy_format(proxy):
                validated_proxies.append(proxy)
        
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
            if url.startswith('tg://'):
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
            else:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
            
            server = params.get('server', [None])[0]
            port = params.get('port', [None])[0]
            secret = params.get('secret', [None])[0]
            
            if not server or not port:
                return None
            
            return ProxyData(
                proxy_type='mtproto',
                server=server,
                port=port,
                secret=secret,
                original_url=url
            )
        except Exception:
            return None
    
    def parse_socks5_url(self, url: str):
        try:
            if url.startswith('tg://'):
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
            else:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
            
            server = params.get('server', [None])[0]
            port = params.get('port', [None])[0]
            username = params.get('user', [None])[0]
            password = params.get('pass', [None])[0]
            
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
        except Exception:
            return None
    
    def parse_http_url(self, url: str):
        try:
            if url.startswith('tg://'):
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
            else:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
            
            server = params.get('server', [None])[0]
            port = params.get('port', [None])[0]
            
            if not server or not port:
                return None
            
            return ProxyData(
                proxy_type='http',
                server=server,
                port=port,
                original_url=url
            )
        except Exception:
            return None
    
    def validate_proxy_format(self, proxy_data: ProxyData):
        if not proxy_data or not proxy_data.server or not proxy_data.port:
            return False
        
        if not self._is_valid_ip_or_domain(proxy_data.server):
            return False
        
        try:
            port_num = int(proxy_data.port)
            if port_num < 1 or port_num > 65535:
                return False
        except ValueError:
            return False
        
        if proxy_data.proxy_type == 'mtproto':
            if proxy_data.secret and not self._is_valid_hex_secret(proxy_data.secret):
                return False
        
        return True
    
    def _is_valid_ip_or_domain(self, address: str):
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        domain_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        
        if re.match(ip_pattern, address):
            parts = address.split('.')
            return all(0 <= int(part) <= 255 for part in parts)
        
        return bool(re.match(domain_pattern, address))
    
    def _is_valid_hex_secret(self, secret: str):
        return bool(re.match(r'^[a-fA-F0-9]+$', secret)) and len(secret) % 2 == 0 