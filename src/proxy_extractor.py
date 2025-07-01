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
        # Main pattern to extract t.me/proxy links
        self.telegram_proxy_pattern = r'(?:@)?(?:https?://)?t\.me/proxy\?server=([^&\s]+)&port=(\d+)&secret=([^&\s]+)'
        
        # Additional pattern for hypertext links
        self.hypertext_pattern = r'href=["\']((?:https?://)?t\.me/proxy\?[^"\']+)["\']'
    
    def extract_all_proxies(self, text: str):
        if not text:
            return []
        
        # Clean up text - replace HTML entities and normalize spaces
        cleaned_text = text.replace('&amp;', '&')
        
        # Extract hypertext links first
        hypertext_links = self.extract_hypertext_links(cleaned_text)
        
        all_proxies = []
        
        # Process hypertext links
        for link in hypertext_links:
            try:
                # Extract parameters from the hypertext link
                match = re.search(self.telegram_proxy_pattern, link)
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
                    
                    # Clean up server name
                    server = re.sub(r'[Pp]ort$', '', server).strip()
                    
                    full_url = f"https://t.me/proxy?server={server}&port={port}&secret={secret}"
                    
                    proxy = ProxyData(
                        proxy_type='mtproto',
                        server=server,
                        port=port,
                        secret=secret,
                        original_url=full_url
                    )
                    all_proxies.append(proxy)
            except Exception as e:
                print(f"Error parsing hypertext link: {type(e).__name__}: {e}")
        
        # Extract all t.me/proxy links from plain text
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
            except Exception as e:
                print(f"Error parsing proxy URL: {type(e).__name__}: {e}")
        
        # Deduplicate proxies by server:port
        unique_proxies = []
        seen_servers = set()
        
        for proxy in all_proxies:
            server_port = f"{proxy.server}:{proxy.port}"
            if server_port not in seen_servers:
                seen_servers.add(server_port)
                unique_proxies.append(proxy)
        
        print(f"Found {len(unique_proxies)} potential proxies in text")
        
        validated_proxies = []
        for proxy in unique_proxies:
            if self.validate_proxy_format(proxy):
                validated_proxies.append(proxy)
            else:
                print(f"Invalid proxy format: {proxy.server}:{proxy.port} ({proxy.proxy_type})")
        
        print(f"Validated {len(validated_proxies)} proxies with correct format")
        return validated_proxies
    
    def extract_hypertext_links(self, text: str):
        """Extract links from hypertext/HTML content"""
        links = []
        
        # Find all href attributes that contain t.me/proxy
        matches = re.finditer(self.hypertext_pattern, text, re.IGNORECASE)
        for match in matches:
            link = match.group(1)
            links.append(link)
        
        return links
    
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
        
        # Be lenient with secret validation - just check if it exists
        if proxy_data.proxy_type == 'mtproto' and not proxy_data.secret:
            print(f"Missing MTProto secret")
            return False
        
        return True
    
    def _is_valid_ip_or_domain(self, address: str):
        # Very lenient IP/domain validation - just check if it's not empty and doesn't contain spaces
        if not address or ' ' in address:
            return False
        
        # Allow most characters that could be in a domain or complex server name
        return True 