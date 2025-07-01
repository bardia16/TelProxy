# Telegram Proxy Scraper

A Python project to scrape specific Telegram channels for extracting Telegram proxy links (MTProto and SOCKS5 proxies).

## Features

- **Comprehensive Scraping**: Extracts proxy links from text, hyperlinks, and inline buttons
- **Multi-Format Support**: MTProto, SOCKS5, and HTTP proxy detection
- **Real Connectivity Testing**: Validates proxies with actual connection tests
- **Dual Storage**: Local SQLite database + JSON export for offline access
- **Automated Telegram Posting**: Hourly updates with message pinning
- **Historical Tracking**: Maintains posting history and statistics
- **Clean Architecture**: Modular design following SOLID principles

## Requirements

- Python 3.8+
- Telegram API credentials (api_id and api_hash)

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

## Getting Telegram API Credentials

1. Go to https://my.telegram.org
2. Login with your phone number
3. Go to "API Development Tools"
4. Create a new application to get `api_id` and `api_hash`

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

**Local Storage Only**: Configure only API credentials - proxies saved to JSON and SQLite database

**Combined Method (Recommended)**: Configure API credentials + output channel - proxies posted to Telegram with automatic pinning and historical tracking

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