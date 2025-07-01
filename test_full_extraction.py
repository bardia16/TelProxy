import asyncio
import html
from bs4 import BeautifulSoup
from src.proxy_extractor import ProxyExtractor
from src.channel_scraper import ChannelScraper
from src.telegram_client import TelegramClient

# Sample HTML with proxy links
sample_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Telegram: Contact @iMTProto</title>
</head>
<body>
    <div class="tgme_widget_message_wrap">
        <div class="tgme_widget_message" data-post="iMTProto/123">
            <div class="tgme_widget_message_text">
                <a class="anchor-url" href="https://t.me/proxy?server=140.233.187.135&amp;port=343&amp;secret=eed77db43ee3721f0fcb40a4ff63b5cd276D656469612E737465616D706F77657265642E636F6D" onclick="im(this)">پروکسی</a>
                
                <p>Some text with a proxy link: <a href="https://t.me/proxy?server=91.107.180.22&port=27&secret=7gAAAAAAAAAAAAAAAAAAAABtZWRpYS5zdGVhbXBvd2VyZWQuY29t">MTProto Proxy</a></p>
                
                <div>Another proxy: <a href="https://t.me/proxy?server=91.99.184.103&port=888&secret=dd00000000000000000000000000000000">Connect</a></div>
            </div>
            <div class="tgme_widget_message_date">
                <time datetime="2025-07-01T12:00:00+00:00">12:00</time>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Mock TelegramClient for testing
class MockTelegramClient(TelegramClient):
    async def get_channel_messages(self, channel_url, limit=100):
        # Parse the sample HTML
        soup = BeautifulSoup(sample_html, 'html.parser')
        
        # Find all message containers
        message_containers = soup.find_all('div', class_='tgme_widget_message')
        
        messages = []
        for container in message_containers:
            message_id = container.get('data-post', '').split('/')[-1]
            
            # Get message text
            text_div = container.find('div', class_='tgme_widget_message_text')
            text = text_div.get_text() if text_div else ''
            
            # Get the full HTML content of the message
            html_content = str(text_div) if text_div else ''
            
            # Get message date
            date_span = container.find('span', class_='tgme_widget_message_date')
            date_str = date_span.find('time').get('datetime') if date_span and date_span.find('time') else ''
            from datetime import datetime
            date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00')) if date_str else datetime.now()
            
            # Extract all href attributes from a tags
            hrefs = []
            if text_div:
                for a_tag in text_div.find_all('a'):
                    href = a_tag.get('href')
                    if href:
                        hrefs.append(href)
                        
                        # Debug print for proxy links
                        if 't.me/proxy' in href:
                            print(f"Found proxy link in href: {href}")
            
            # Create message data structure
            message_data = {
                'id': message_id,
                'channel_id': 'iMTProto',
                'channel_name': 'iMTProto',
                'date': date_obj.strftime('%Y-%m-%d %H:%M:%S'),
                'text': text,
                'html': html_content,
                'hrefs': hrefs,
                'combined_text': text + ' ' + html_content
            }
            
            messages.append(message_data)
        
        return messages

async def test_full_extraction():
    print("🧪 Testing Full Extraction Pipeline")
    print("-" * 60)
    
    # Create mock client and scraper
    mock_client = MockTelegramClient()
    await mock_client.start_session()
    
    channel_scraper = ChannelScraper(mock_client)
    proxy_extractor = ProxyExtractor()
    
    # Simulate scraping a channel
    channel_entity = await mock_client.get_channel_entity('iMTProto')
    messages = await mock_client.fetch_channel_messages(channel_entity)
    
    # Filter relevant messages
    relevant_messages = channel_scraper.filter_relevant_messages(messages)
    
    print(f"\n📋 Found {len(relevant_messages)} relevant messages")
    
    # Extract proxies from messages
    all_proxies = []
    for message in relevant_messages:
        # Extract proxies from href attributes and text content
        proxies = proxy_extractor.extract_all_proxies(
            hrefs=message.get('hrefs', []),
            text=message.get('combined_text', '')
        )
        all_proxies.extend(proxies)
    
    print("\n🔍 Extracted Proxies:")
    print("-" * 60)
    print(f"{'Server':<30} {'Port':<8} {'Secret':<20}")
    print("-" * 60)
    
    for proxy in all_proxies:
        secret_preview = proxy.secret[:10] + "..." if len(proxy.secret) > 10 else proxy.secret
        print(f"{proxy.server:<30} {proxy.port:<8} {secret_preview:<20}")
    
    print("-" * 60)
    print(f"Total proxies found: {len(all_proxies)}")

if __name__ == "__main__":
    asyncio.run(test_full_extraction()) 