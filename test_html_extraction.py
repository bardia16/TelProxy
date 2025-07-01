import asyncio
from src.proxy_extractor import ProxyExtractor

# Sample HTML with proxy links
sample_html = """
<div class="message-text">
    <a class="anchor-url" href="https://t.me/proxy?server=140.233.187.135&amp;port=343&amp;secret=eed77db43ee3721f0fcb40a4ff63b5cd276D656469612E737465616D706F77657265642E636F6D" onclick="im(this)">پروکسی</a>
    
    <p>Some text with a proxy link: <a href="https://t.me/proxy?server=91.107.180.22&port=27&secret=7gAAAAAAAAAAAAAAAAAAAABtZWRpYS5zdGVhbXBvd2VyZWQuY29t">MTProto Proxy</a></p>
    
    <div>Another proxy: <a href="https://t.me/proxy?server=91.99.184.103&port=888&secret=dd00000000000000000000000000000000">Connect</a></div>
</div>
"""

async def test_extraction():
    print("🧪 Testing HTML proxy extraction")
    print("-" * 60)
    
    # Create extractor
    extractor = ProxyExtractor()
    
    # Extract hrefs from HTML using BeautifulSoup
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(sample_html, 'html.parser')
    hrefs = [a.get('href') for a in soup.find_all('a')]
    
    print(f"Found {len(hrefs)} href attributes in HTML:")
    for i, href in enumerate(hrefs):
        print(f"  {i+1}. {href}")
    
    # Extract proxies
    proxies = extractor.extract_all_proxies(hrefs=hrefs, text=sample_html)
    
    print("\n🔍 Extracted Proxies:")
    print("-" * 60)
    print(f"{'Server':<30} {'Port':<8} {'Secret':<20}")
    print("-" * 60)
    
    for proxy in proxies:
        secret_preview = proxy.secret[:10] + "..." if len(proxy.secret) > 10 else proxy.secret
        print(f"{proxy.server:<30} {proxy.port:<8} {secret_preview:<20}")
    
    print("-" * 60)
    print(f"Total proxies found: {len(proxies)}")

if __name__ == "__main__":
    asyncio.run(test_extraction()) 