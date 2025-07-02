import base64
import asyncio
import logging
from telethon import TelegramClient, connection
from config.settings import API_ID, API_HASH, INITIAL_PROXY

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get proxy details from settings
host = INITIAL_PROXY['server']
port = int(INITIAL_PROXY['port'])
secret_base64 = INITIAL_PROXY['secret']

# Process the secret
if secret_base64.startswith('7'):
    secret_base64 = secret_base64[1:]
    logger.debug(f"Secret after removing '7' prefix: {secret_base64}")

# Add padding if needed
missing_padding = len(secret_base64) % 4
if missing_padding:
    secret_base64 += '=' * (4 - missing_padding)
    logger.debug(f"Secret after padding: {secret_base64}")

# Convert to hex
secret_bytes = base64.b64decode(secret_base64)
secret_hex = secret_bytes.hex()

logger.debug(f"Proxy configuration:")
logger.debug(f"Host: {host}")
logger.debug(f"Port: {port}")
logger.debug(f"Secret (hex): {secret_hex}")

async def test_connection():
    # Create the client
    client = TelegramClient(
        'anon',  # Session name
        API_ID,
        API_HASH,
        connection=connection.ConnectionTcpMTProxyIntermediate,  # Try intermediate first
        proxy=(host, port, secret_hex)
    )
    
    try:
        logger.info("Connecting to Telegram...")
        await client.connect()
        
        if await client.is_user_authorized():
            logger.info("Already authorized")
            me = await client.get_me()
            logger.info(f"Connected as: {me.first_name} (@{me.username})")
        else:
            logger.info("Not authorized, but connection successful")
        
        logger.info("Testing connection to Telegram servers...")
        # Try to get Telegram's help/support user as a connection test
        support = await client.get_entity('telegram')
        logger.info(f"Successfully retrieved @telegram: {support.first_name}")
        
    except Exception as e:
        logger.error(f"Error during connection test: {e}", exc_info=True)
        raise
    finally:
        await client.disconnect()
        logger.info("Disconnected")

if __name__ == '__main__':
    asyncio.run(test_connection()) 