import json
import sqlite3
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Optional
from pathlib import Path
from telethon import TelegramClient as TelethonClient
from telethon.tl.functions.channels import UpdatePinnedMessageRequest
from src.proxy_extractor import ProxyData
from config.settings import STORAGE_FILE_PATH, API_ID, API_HASH, SESSION_NAME


class ProxyStorage:
    
    def __init__(self, telegram_client=None, output_channel=None):
        self.storage_path = Path(STORAGE_FILE_PATH)
        self.db_path = Path('data/proxies.db')
        self.telegram_client = telegram_client
        self.output_channel = output_channel
        self.last_posted_message_id = None
        self._ensure_storage_directories()
        self._initialize_database()
    
    def _ensure_storage_directories(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _initialize_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proxy_type TEXT NOT NULL,
                    server TEXT NOT NULL,
                    port TEXT NOT NULL,
                    secret TEXT,
                    username TEXT,
                    password TEXT,
                    original_url TEXT,
                    is_working BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_validated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(server, port, proxy_type)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS posting_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    message_id INTEGER,
                    proxy_count INTEGER,
                    channel_id TEXT
                )
            ''')
            conn.commit()
    
    def save_proxies_to_json(self, proxies: List[ProxyData]):
        data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_proxies': len(proxies),
            'proxies': []
        }
        
        for proxy in proxies:
            proxy_dict = {
                'proxy_type': proxy.proxy_type,
                'server': proxy.server,
                'port': proxy.port,
                'secret': proxy.secret,
                'username': proxy.username,
                'password': proxy.password,
                'original_url': proxy.original_url
            }
            data['proxies'].append(proxy_dict)
        
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_proxies_from_json(self):
        if not self.storage_path.exists():
            return []
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            proxies = []
            for proxy_dict in data.get('proxies', []):
                proxy = ProxyData(
                    proxy_type=proxy_dict['proxy_type'],
                    server=proxy_dict['server'],
                    port=proxy_dict['port'],
                    secret=proxy_dict.get('secret'),
                    username=proxy_dict.get('username'),
                    password=proxy_dict.get('password'),
                    original_url=proxy_dict.get('original_url', '')
                )
                proxies.append(proxy)
            
            return proxies
        except Exception as e:
            print(f"Error loading proxies from JSON: {e}")
            return []
    
    def save_proxies_to_database(self, proxies: List[ProxyData]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for proxy in proxies:
                cursor.execute('''
                    INSERT OR REPLACE INTO proxies 
                    (proxy_type, server, port, secret, username, password, original_url, is_working, last_validated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    proxy.proxy_type,
                    proxy.server,
                    proxy.port,
                    proxy.secret,
                    proxy.username,
                    proxy.password,
                    proxy.original_url,
                    True,
                    datetime.now(timezone.utc)
                ))
            
            conn.commit()
    
    def load_proxies_from_database(self, proxy_type: Optional[str] = None, working_only: bool = True):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if proxy_type:
                if working_only:
                    cursor.execute(
                        'SELECT * FROM proxies WHERE proxy_type = ? AND is_working = 1 ORDER BY last_validated DESC',
                        (proxy_type,)
                    )
                else:
                    cursor.execute(
                        'SELECT * FROM proxies WHERE proxy_type = ? ORDER BY last_validated DESC',
                        (proxy_type,)
                    )
            else:
                if working_only:
                    cursor.execute('SELECT * FROM proxies WHERE is_working = 1 ORDER BY last_validated DESC')
                else:
                    cursor.execute('SELECT * FROM proxies ORDER BY last_validated DESC')
            
            rows = cursor.fetchall()
            proxies = []
            
            for row in rows:
                proxy = ProxyData(
                    proxy_type=row[1],
                    server=row[2],
                    port=row[3],
                    secret=row[4],
                    username=row[5],
                    password=row[6],
                    original_url=row[7]
                )
                proxies.append(proxy)
            
            return proxies
    
    def update_proxy_status(self, proxy: ProxyData, is_working: bool):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE proxies 
                SET is_working = ?, last_validated = ?
                WHERE server = ? AND port = ? AND proxy_type = ?
            ''', (
                is_working,
                datetime.now(timezone.utc),
                proxy.server,
                proxy.port,
                proxy.proxy_type
            ))
            conn.commit()
    
    def get_working_proxies(self):
        return self.load_proxies_from_database(working_only=True)
    
    def get_proxies_by_type(self, proxy_type: str):
        return self.load_proxies_from_database(proxy_type=proxy_type)
    
    def remove_outdated_proxies(self, days_old: int = 7):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cutoff_date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ).timestamp() - (days_old * 24 * 3600)
            
            cursor.execute(
                'DELETE FROM proxies WHERE last_validated < datetime(?, "unixepoch")',
                (cutoff_date,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            
            print(f"Removed {deleted_count} outdated proxies older than {days_old} days")
            return deleted_count
    
    def export_proxies_to_text(self, output_file: str):
        proxies = self.get_working_proxies()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Telegram Proxies Export - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n")
            f.write(f"# Total working proxies: {len(proxies)}\n\n")
            
            by_type = {}
            for proxy in proxies:
                if proxy.proxy_type not in by_type:
                    by_type[proxy.proxy_type] = []
                by_type[proxy.proxy_type].append(proxy)
            
            for proxy_type, proxy_list in by_type.items():
                f.write(f"## {proxy_type.upper()} Proxies ({len(proxy_list)})\n")
                for proxy in proxy_list:
                    if proxy.original_url:
                        f.write(f"{proxy.original_url}\n")
                    else:
                        f.write(f"{proxy.server}:{proxy.port}\n")
                f.write("\n")
    
    async def post_proxies_to_telegram(self, proxies: List[ProxyData]):
        if not self.telegram_client or not self.output_channel:
            print("Telegram client or output channel not configured for posting")
            return None
        
        try:
            message = self._format_proxy_message(proxies)
            
            sent_message = await self.telegram_client.client.send_message(
                self.output_channel, message, parse_mode='markdown'
            )
            
            await self._pin_latest_message(sent_message.id)
            
            self._record_posting_history(sent_message.id, len(proxies))
            
            print(f"✅ Posted {len(proxies)} proxies to Telegram channel")
            return sent_message.id
            
        except Exception as e:
            print(f"❌ Error posting to Telegram: {e}")
            return None
    
    def _format_proxy_message(self, proxies: List[ProxyData]):
        now = datetime.now(timezone.utc)
        timestamp = now.strftime('%Y-%m-%d %H:%M UTC')
        
        message_lines = [
            f"🔑 **Hourly Proxy Update** [{timestamp}]",
            f"📊 **Total Proxies:** {len(proxies)}",
            ""
        ]
        
        by_type = {}
        for proxy in proxies:
            if proxy.proxy_type not in by_type:
                by_type[proxy.proxy_type] = []
            by_type[proxy.proxy_type].append(proxy)
        
        for proxy_type, proxy_list in by_type.items():
            message_lines.append(f"**{proxy_type.upper()} ({len(proxy_list)}):**")
            for proxy in proxy_list:
                if proxy.original_url:
                    message_lines.append(f"• `{proxy.original_url}`")
                else:
                    url = self._reconstruct_proxy_url(proxy)
                    message_lines.append(f"• `{url}`")
            message_lines.append("")
        
        message_lines.append("🔄 *Next update in 1 hour*")
        return "\n".join(message_lines)
    
    def _reconstruct_proxy_url(self, proxy: ProxyData):
        if proxy.proxy_type == 'mtproto':
            url = f"tg://proxy?server={proxy.server}&port={proxy.port}"
            if proxy.secret:
                url += f"&secret={proxy.secret}"
        elif proxy.proxy_type == 'socks5':
            url = f"tg://socks?server={proxy.server}&port={proxy.port}"
            if proxy.username and proxy.password:
                url += f"&user={proxy.username}&pass={proxy.password}"
        elif proxy.proxy_type == 'http':
            url = f"tg://http?server={proxy.server}&port={proxy.port}"
        else:
            url = f"{proxy.server}:{proxy.port}"
        
        return url
    
    async def _pin_latest_message(self, message_id: int):
        try:
            if self.last_posted_message_id:
                await self.telegram_client.client(UpdatePinnedMessageRequest(
                    channel=self.output_channel,
                    id=0,
                    unpin=True
                ))
            
            await self.telegram_client.client(UpdatePinnedMessageRequest(
                channel=self.output_channel,
                id=message_id,
                silent=True
            ))
            
            self.last_posted_message_id = message_id
            print("📌 Message pinned successfully")
            
        except Exception as e:
            print(f"⚠️ Could not pin message: {e}")
    
    def _record_posting_history(self, message_id: int, proxy_count: int):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO posting_history (message_id, proxy_count, channel_id)
                VALUES (?, ?, ?)
            ''', (message_id, proxy_count, str(self.output_channel)))
            conn.commit()
    
    def get_posting_stats(self, days: int = 7):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_posts,
                    SUM(proxy_count) as total_proxies,
                    AVG(proxy_count) as avg_proxies_per_post,
                    MAX(posted_at) as last_post
                FROM posting_history 
                WHERE posted_at > datetime('now', '-{} days')
            '''.format(days))
            
            result = cursor.fetchone()
            return {
                'total_posts': result[0] or 0,
                'total_proxies': result[1] or 0,
                'avg_proxies_per_post': round(result[2] or 0, 1),
                'last_post': result[3] or 'Never'
            } 