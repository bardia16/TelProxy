import re
import urllib.parse
from typing import List, Dict, Optional
from dataclasses import dataclass
import html


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
        # Main pattern to extract t.me/proxy links
        self.telegram_proxy_pattern = r'(?:@)?(?:https?://)?t\.me/proxy\?server=([^&\s]+)&port=(\d+)&secret=([^&\s]+)'
    
    def extract_all_proxies(self, hrefs: List[str], text: str = ""):
        """Extract proxies from a list of href values and optional text"""
        if not hrefs and not text:
            return []
        
        all_proxies = []
        
        # Process all href values
        for href in hrefs:
            try:
                # Unescape HTML entities in the href
                href = html.unescape(href)
                
                # Check if this is a t.me/proxy link
                if 't.me/proxy' in href:
                    match = re.search(self.telegram_proxy_pattern, href)
                    if match:
                        server = match.group(1)
                        port = match.group(2)
                        secret = match.group(3)
                        
                        # URL decode the secret if it's URL encoded
                        try:
                            decoded_secret = urllib.parse.unquote(secret)
                            if decoded_secret != secret:
                                secret = decoded_secret
                        except Exception:
                            pass
                        
                        # Clean up server name - remove any trailing "Port" text
                        server = re.sub(r'[Pp]ort$', '', server).strip()
                        
                        full_url = f"https://t.me/proxy?server={server}&port={port}&secret={secret}"
                        
                        proxy = ProxyData(
                            proxy_type='mtproto',  # All t.me/proxy links are MTProto
                            server=server,
                            port=port,
                            secret=secret,
                            original_url=full_url
                        )
                        all_proxies.append(proxy)
            except Exception:
                pass
        
        # Also check text content for plain text links
        if text:
            cleaned_text = html.unescape(text)
            matches = re.finditer(self.telegram_proxy_pattern, cleaned_text, re.IGNORECASE)
            for match in matches:
                try:
                    server = match.group(1)
                    port = match.group(2)
                    secret = match.group(3)
                    
                    # URL decode the secret if it's URL encoded
                    try:
                        decoded_secret = urllib.parse.unquote(secret)
                        if decoded_secret != secret:
                            secret = decoded_secret
                    except Exception:
                        pass
                    
                    # Clean up server name - remove any trailing "Port" text
                    server = re.sub(r'[Pp]ort$', '', server).strip()
                    
                    full_url = f"https://t.me/proxy?server={server}&port={port}&secret={secret}"
                    
                    proxy = ProxyData(
                        proxy_type='mtproto',  # All t.me/proxy links are MTProto
                        server=server,
                        port=port,
                        secret=secret,
                        original_url=full_url
                    )
                    all_proxies.append(proxy)
                except Exception:
                    continue
        
        # Deduplicate proxies by server:port
        unique_proxies = []
        seen_servers = set()
        
        for proxy in all_proxies:
            server_port = f"{proxy.server}:{proxy.port}"
            if server_port not in seen_servers:
                seen_servers.add(server_port)
                unique_proxies.append(proxy)
        
        # Validate proxy format
        validated_proxies = []
        for proxy in unique_proxies:
            if self.validate_proxy_format(proxy):
                validated_proxies.append(proxy)
        
        return validated_proxies
    
    def validate_proxy_format(self, proxy_data: ProxyData):
        if not proxy_data or not proxy_data.server or not proxy_data.port:
            return False
        
        # Be more lenient with IP/domain validation
        if not self._is_valid_ip_or_domain(proxy_data.server):
            return False
        
        try:
            port_num = int(proxy_data.port)
            if port_num < 1 or port_num > 65535:
                return False
        except ValueError:
            return False
        
        # Be lenient with secret validation - just check if it exists
        if proxy_data.proxy_type == 'mtproto' and not proxy_data.secret:
            return False
        
        return True
    
    def _is_valid_ip_or_domain(self, address: str):
        # Very lenient IP/domain validation - just check if it's not empty and doesn't contain spaces
        if not address or ' ' in address:
            return False
        
        # Allow most characters that could be in a domain or complex server name
        return True
    
    @staticmethod
    def remove_duplicates(proxies: List[ProxyData]) -> List[ProxyData]:
        """Remove duplicate proxies based on server, port, and proxy type combination"""
        if not proxies:
            return []
        
        unique_proxies = []
        seen_combinations = set()
        
        for proxy in proxies:
            # Create unique identifier including proxy type for more precise deduplication
            proxy_key = f"{proxy.proxy_type}:{proxy.server}:{proxy.port}"
            
            # For MTProto proxies, also include secret in the key since different secrets
            # on the same server:port represent different proxy configurations
            if proxy.proxy_type == 'mtproto' and proxy.secret:
                proxy_key += f":{proxy.secret}"
            
            # For SOCKS5 proxies, include username if available
            elif proxy.proxy_type == 'socks5' and proxy.username:
                proxy_key += f":{proxy.username}"
            
            if proxy_key not in seen_combinations:
                seen_combinations.add(proxy_key)
                unique_proxies.append(proxy)
        
        return unique_proxies 