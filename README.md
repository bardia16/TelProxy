# Telegram Proxy Scraper

A Python project to scrape specific Telegram channels for extracting Telegram proxy links (MTProto and SOCKS5 proxies).

## Features

- Scrapes public Telegram channels for proxy links
- Extracts MTProto and SOCKS5 proxy URLs using pattern recognition
- Validates proxy connectivity
- Stores proxies in local storage for offline access
- Modular, clean architecture following SOLID principles

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
4. Configure your Telegram API credentials in `config/settings.py`
5. Specify target channels in `config/channels.py`

## Getting Telegram API Credentials

1. Go to https://my.telegram.org
2. Login with your phone number
3. Go to "API Development Tools"
4. Create a new application to get `api_id` and `api_hash`

## Usage

```bash
python -m src.main
```

## Project Structure

```
telegram_proxy/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── telegram_client.py
│   ├── channel_scraper.py
│   ├── proxy_extractor.py
│   ├── proxy_validator.py
│   └── proxy_storage.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   └── channels.py
├── tests/
│   └── __init__.py
├── data/
│   └── .gitkeep
├── requirements.txt
├── .gitignore
└── README.md
```

## License

MIT License 