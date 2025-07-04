import os
from dotenv import load_dotenv

load_dotenv()

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE_NUMBER = os.getenv('TELEGRAM_PHONE_NUMBER')

# Bot token can be used instead of API_ID/API_HASH/PHONE_NUMBER
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

OUTPUT_CHANNEL = os.getenv('TELEGRAM_OUTPUT_CHANNEL')

SESSION_NAME = 'telegram_scraper'

PROXY_VALIDATION_TIMEOUT = 5

# Ping measurement settings
PING_MEASUREMENTS = 5  # Number of ping tests to average
PING_DELAY = 0.2  # Delay between ping measurements in seconds

STORAGE_FILE_PATH = 'data/proxies.json'

RATE_LIMIT_DELAY = 1

SCHEDULER_INTERVAL_HOURS = 1

TOP_N_PROXIES = 50