import orjson
import sqlite3
import requests
import time
import math
import logging

CACHE_EXPIRE_TIME = 60 * 60 * 12

logger = logging.getLogger('EmojiStore')

class EmojiStore:

    def __init__(self, db, **kwargs):
        self.db: sqlite3.Connection = db
        self.db.row_factory = sqlite3.Row
        cur = self.db.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS emoji_cache(host TEXT, data TEXT, last_updated INTEGER)')
        cur.close()

        self.emoji_cache = {}
        if kwargs.get('session'):
            self.session = kwargs['session']
        else:
            self.session = requests.Session()
            self.session.headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
    
    def _generate_emoji_url(self, host, emoji: dict):
        if emoji.get('url'):
            return emoji['url']
        else:
            # v>=13?
            return f'https://{host}/emoji/{emoji["name"]}.webp'
    
    def _fetch_nodeinfo(self, host):
        r = self.session.get(f'https://{host}/.well-known/nodeinfo')
        if r.status_code != 200:
            logger.getChild('fetch_nodeinfo').error(f'Failed to fetch nodeinfo for {host} (well-known/nodeinfo)')
            raise Exception(f'Failed to fetch nodeinfo for {host}')
        res = orjson.loads(r.content)
        if res.get('links'):
            for link in res['links']:
                if link['rel'].endswith('nodeinfo.diaspora.software/ns/schema/2.0'):
                    r2 = self.session.get(link['href'])
                    if r2.status_code != 200:
                        logger.getChild('fetch_nodeinfo').error(f'Failed to fetch nodeinfo for {host} (nodeinfo)')
                        raise Exception(f'Failed to fetch nodeinfo for {host}')
                    return orjson.loads(r2.content)
        logger.getChild('fetch_nodeinfo').error(f'Failed to fetch nodeinfo for {host}')
        raise Exception(f'Failed to fetch nodeinfo for {host}')
    
    def _fetch_emoji_data(self, host):
        logger.getChild('fetch_emoji_data').info(f'Fetching emoji data for {host}')
        try:
            ni = self._fetch_nodeinfo(host)
            r = self.session.post(f'https://{host}/api/meta', headers={'Content-Type': 'application/json'}, data=b'{}')
            if r.status_code != 200 and r.status_code != 404:
                logger.getChild('fetch_emoji_data').error(f'Failed to fetch emoji data for {host} (api/meta)')
                raise Exception(f'Failed to fetch emoji data for {host}')
            if r.status_code != 404:
                meta = orjson.loads(r.content)
                v = meta['version'].split('.')
                # Misskey v13以降は別エンドポイントに問い合わせ
                if ni['software']['name'] == 'misskey' and int(v[0]) >= 13:
                    r2 = self.session.post(f'https://{host}/api/emojis', headers={'Content-Type': 'application/json'}, data=b'{}')
                    if r2.status_code != 200:
                        logger.getChild('fetch_emoji_data').error(f'Failed to fetch emoji data for {host} (Misskey v13)')
                        raise Exception(f'Failed to fetch emoji data for {host} (Misskey v13)')
                    return orjson.loads(r2.content)['emojis']
                else:
                    return meta['emojis']
            else:
                # Mastodon/Pleroma?
                r3 = self.session.get(f'https://{host}/api/v1/custom_emojis')
                if r3.status_code != 200:
                    logger.getChild('fetch_emoji_data').error(f'Failed to fetch emoji data for {host} (mastodon, pleroma)')
                    raise Exception(f'Failed to fetch emoji data for {host} (mastodon, pleroma)')
                res = orjson.loads(r3.content)
                # Misskey形式に変換
                return [{'name': x['shortcode'], 'url': x['static_url'], 'aliases': [''], 'category': ''} for x in res]
        except:
            return []
    
    def _download(self, host):
        emoji_data = self._fetch_emoji_data(host)
        cur = self.db.cursor()
        cur.execute('REPLACE INTO emoji_cache(host, data, last_updated) VALUES (?, ?, ?)', (host, orjson.dumps(emoji_data), math.floor(time.time())))
        self.db.commit()
        self.emoji_cache[host] = emoji_data

    def _load(self, host) -> list:
        emojis = []
        if host in self.emoji_cache.keys():
            emojis = self.emoji_cache[host]
        else:
            cur = self.db.cursor()
            cur.execute('SELECT * FROM emoji_cache WHERE host = ?', (host,))
            row = cur.fetchone()
            if row is None:
                logger.getChild('load').error(f'emoji data not found. fetching')
                self._download(host)
                return self._load(host)
            else:
                expire = CACHE_EXPIRE_TIME
                # 前回取得失敗してる？
                if row['data'] == '[]':
                    expire = 60 * 5
                if math.floor(time.time()) - row['last_updated'] > expire:
                    logger.getChild('load').error(f'emoji cache expired. refreshing')
                    self._download(host)
                    return self._load(host)
            self.emoji_cache[host] = orjson.loads(row['data'])
            emojis = self.emoji_cache[host]
        
        return emojis
    
    # ----------------------

    def refresh(self, host):
        self._download(host)
    
    def find_by_keyword(self, host, k) -> list:
        emojis = self._load(host)
        res = []
        for emoji in emojis:
            if k in emoji['name'].lower():
                res.append({'name': emoji['name'], 'url': self._generate_emoji_url(host, emoji)})
        return res
    
    def find_by_alias(self, host, t) -> list:
        emojis = self._load(host)
        res = []
        for emoji in emojis:
            if t in emoji['aliases']:
                res.append({'name': emoji['name'], 'url': self._generate_emoji_url(host, emoji)})
        return res
    
    def get(self, host, name):
        emojis = self._load(host)
        for emoji in emojis:
            if emoji['name'] == name:
                return {'name': emoji['name'], 'url': self._generate_emoji_url(host, emoji)}
        return None