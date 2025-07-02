# Telegram Proxy Scraper

A Python project to scrape specific Telegram channels for extracting Telegram proxy links (MTProto and SOCKS5 proxies).

## Features

- **Comprehensive Scraping**: Extracts proxy links from text, hyperlinks, and inline buttons
- **Multi-Format Support**: MTProto, SOCKS5, and HTTP proxy detection
- **Proxy-Enhanced Scraping**: Uses Telegram proxies for web scraping to bypass restrictions
- **Real Connectivity Testing**: Validates proxies with actual connection tests
- **Dual Storage**: Local SQLite database + JSON export for offline access
- **Automated Telegram Posting**: Hourly updates with message pinning
- **Historical Tracking**: Maintains posting history and statistics
- **Clean Architecture**: Modular design following SOLID principles

## Requirements

- Python 3.8+
- Either:
  - Telegram API credentials (api_id and api_hash), or
  - Telegram Bot Token (easier option)

## Setup

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create `.env` file and configure credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```
5. Configure target channels in `config/channels.py`
6. (Optional) Set `TELEGRAM_OUTPUT_CHANNEL` for automated posting

## Authentication Options

You can authenticate with Telegram in one of two ways:

### Option 1: Telegram API Credentials (User Account)

1. Go to https://my.telegram.org
2. Login with your phone number
3. Go to "API Development Tools"
4. Create a new application to get `api_id` and `api_hash`
5. Add to your `.env` file:
   ```
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_PHONE_NUMBER=your_phone_number
   ```

### Option 2: Bot Token (Recommended)

1. Talk to [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot` command
3. Get your bot token
4. Add to your `.env` file:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   ```

## Configuration

You can customize the behavior by modifying `config/settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `TOP_N_PROXIES` | 50 | Maximum number of best-performing proxies to post to Telegram (sorted by ping time) |
| `PROXY_VALIDATION_TIMEOUT` | 10 | Timeout in seconds for proxy connectivity tests |
| `PING_MEASUREMENTS` | 5 | Number of ping tests to average for each proxy |
| `PING_DELAY` | 0.2 | Delay in seconds between ping measurements |
| `RATE_LIMIT_DELAY` | 1 | Delay in seconds between API requests |
| `SCHEDULER_INTERVAL_HOURS` | 1 | Interval in hours for automated runs |
| `CHANNEL_MESSAGE_LIMIT` | 200 | Maximum number of messages to scrape from each channel |
| `USE_PROXY_FOR_SCRAPING` | True | Enable using Telegram proxies for web scraping |
| `SCRAPING_PROXY_TYPE` | 'http' | Proxy type preference: 'http', 'socks5', or 'auto' |
| `SCRAPING_PROXY_TIMEOUT` | 10 | Timeout in seconds for proxy-enabled web requests |

## Usage

### Single Run (Extract & Validate Once)
```bash
python -m src.main once
```

### Scheduled Hourly Runs (Automated)
```bash
python -m src.main schedule
```

### Output Modes

**Local Storage Only**: Configure only API credentials or bot token - proxies saved to JSON and SQLite database

**Combined Method (Recommended)**: Configure API credentials/bot token + output channel - proxies posted to Telegram with automatic pinning and historical tracking. Only the top N best-performing proxies (lowest ping times) are posted.

## Proxy-Enhanced Web Scraping

The system can use previously discovered Telegram proxies to enhance web scraping reliability:

### How It Works

1. **Proxy Selection**: Automatically selects working proxies from the local database
2. **Type Preference**: Configurable preference for HTTP, SOCKS5, or automatic selection
3. **Fallback Mechanism**: If proxy fails, automatically retries with direct connection
4. **Authentication Support**: SOCKS5 proxies with username/password authentication
5. **Dynamic Configuration**: Proxy settings can be changed without restarting

### Configuration Options

- **Initial Proxy Setup**:
  ```python
  # in config/settings.py
  INITIAL_PROXY = {
      'type': 'mtproto',  # 'mtproto', 'socks5', or 'http'
      'server': '1.2.3.4',
      'port': '443',
      'secret': 'ee...dd',  # for MTProto only
      'username': 'user',   # for SOCKS5 only
      'password': 'pass'    # for SOCKS5 only
  }
  ```

- **Scraping Settings**:
  - **`USE_PROXY_FOR_SCRAPING`**: Enable/disable proxy usage for web scraping
  - **`SCRAPING_PROXY_TYPE`**: 
    - `'http'`: Use HTTP proxies only
    - `'socks5'`: Use SOCKS5 proxies only  
    - `'auto'`: Try HTTP first, fallback to SOCKS5
  - **`SCRAPING_PROXY_TIMEOUT`**: Request timeout when using proxies

### Self-Sustaining Proxy System

The script implements a self-sustaining proxy system:

1. **Initial Bootstrap**:
   - Uses the proxy configured in `INITIAL_PROXY` to start scraping
   - This initial proxy helps access blocked channels

2. **Proxy Discovery**:
   - As the script finds working proxies, it saves them to the database
   - The initial proxy is also saved for future use

3. **Smart Selection**:
   - First tries proxies from the database (newest & working)
   - Falls back to initial proxy if no working proxies found
   - Automatically retries with direct connection if all proxies fail

4. **Continuous Updates**:
   - Each successful scraping run updates the proxy pool
   - Old/non-working proxies are automatically removed
   - System becomes self-sufficient over time

### Benefits

- **Bypass Restrictions**: Access blocked Telegram channels
- **Improved Reliability**: Rotate through multiple proxy servers
- **Rate Limit Avoidance**: Distribute requests across different IP addresses
- **Geographic Diversity**: Access content from different regions

## Project Structure

```
telegram_proxy/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point with CLI options
│   ├── scheduler.py         # Automated hourly execution
│   ├── telegram_client.py   # Telegram API wrapper
│   ├── channel_scraper.py   # Message extraction & parsing
│   ├── proxy_extractor.py   # Proxy URL pattern recognition
│   ├── proxy_validator.py   # Connectivity testing
│   └── proxy_storage.py     # Local & Telegram storage
├── config/
│   ├── __init__.py
│   ├── settings.py          # Configuration management
│   └── channels.py          # Target channels list
├── tests/
│   └── __init__.py
├── data/
│   ├── .gitkeep
│   ├── proxies.json         # JSON export (generated)
│   └── proxies.db           # SQLite database (generated)
├── requirements.txt
├── .env.example             # Environment template
├── .gitignore
└── README.md
```

## License

MIT License 