"""Opt-in RSS processing. News text never receives tools or server credentials."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import http.client
import ipaddress
import json
import re
import socket
import time
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit
import uuid
import xml.etree.ElementTree as ET
from pydantic import BaseModel, Field, ConfigDict
from .store import now_iso, BudgetExceeded


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.blocked = [], 0
    def handle_starttag(self, tag, attrs):
        if tag.lower() in {'script', 'style'}:
            self.blocked += 1
    def handle_endtag(self, tag):
        if tag.lower() in {'script', 'style'}:
            self.blocked = max(0, self.blocked - 1)
        if not self.blocked:
            self.parts.append(' ')
    def handle_data(self, data):
        if not self.blocked:
            self.parts.append(data)


def clean(text):
    parser = PlainText()
    parser.feed(text[:20000])
    return ' '.join(''.join(parser.parts).split())[:5000]


def safe_url(url, allowed):
    p = urlsplit(url)
    if p.scheme != 'https' or not p.hostname or p.hostname.lower() not in allowed or p.username or p.password or p.port not in {None, 443}:
        raise ValueError('URL outside configured HTTPS allowlist')
    if any(ord(c) < 32 for c in url):
        raise ValueError('Invalid URL characters')
    try:
        if not ipaddress.ip_address(p.hostname).is_global:
            raise ValueError('Private IP is forbidden')
    except ValueError as error:
        if 'Private IP' in str(error):
            raise
    return urlunsplit(('https', p.hostname.lower(), p.path or '/', p.query, ''))


class NewsProvider(Protocol):
    def fetch(self) -> list[dict]: ...


class RssProvider:
    def __init__(self, feed_urls, allowed_domains, license_confirmed=False):
        if not license_confirmed:
            raise ValueError('News usage and translation license must be confirmed before fetching')
        self.allowed = {d.lower() for d in allowed_domains}
        self.urls = [safe_url(u, self.allowed) for u in feed_urls]

    def read(self, url):
        p = urlsplit(safe_url(url, self.allowed))
        addresses = [row[4][0] for row in socket.getaddrinfo(p.hostname, 443, type=socket.SOCK_STREAM)]
        if not addresses or any(not ipaddress.ip_address(a).is_global for a in addresses):
            raise ValueError('DNS resolves to non-public network')
        # Pin the checked address; TLS SNI/certificate still use the original hostname.
        connection = http.client.HTTPSConnection(p.hostname, timeout=10)
        address = addresses[0]
        connection._create_connection = lambda addr, timeout, source: socket.create_connection((address, 443), timeout, source)
        try:
            connection.request('GET', p.path + ('?' + p.query if p.query else ''), headers={'Accept-Encoding': 'identity', 'User-Agent': 'NabzCoin/0.1'})
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError('Feed failed or redirected; redirects are not followed')
            if response.getheader('Content-Encoding', 'identity') != 'identity':
                raise ValueError('Compressed feeds unsupported')
            body = response.read(1024 * 1024 + 1)
            if len(body) > 1024 * 1024:
                raise ValueError('Feed too large')
            return body
        finally:
            connection.close()

    def fetch(self):
        items = []
        for url in self.urls:
            body = self.read(url)
            # Only UTF-8 feeds: an encoded DTD must not bypass byte-level checks.
            text = body.decode('utf-8-sig')
            if '\x00' in text or '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
                raise ValueError('XML entities forbidden')
            root = ET.fromstring(text)
            for node in root.findall('.//item')[:100]:
                title, link = clean(node.findtext('title', '')), node.findtext('link', '')
                if not title or not link:
                    continue
                try:
                    canonical = safe_url(link, self.allowed)
                    published = parsedate_to_datetime(node.findtext('pubDate', ''))
                    if published.tzinfo is None:
                        continue
                except (ValueError, TypeError):
                    continue
                items.append(dict(title=title, summary=clean(node.findtext('description', ''))[:500],
                    url=canonical, publisher={'mihansignal.com': 'میهن سیگنال'}.get(urlsplit(url).hostname, urlsplit(url).hostname), published_at=published.astimezone(timezone.utc).isoformat(), demo=False))
        return items


class DemoNewsProvider:
    def fetch(self):
        return [dict(title='Demo: Bitcoin market guide 2026', summary='Sample data only; price is 62450.25 USD.',
            url='https://bitcoin.org/fa/', publisher='Nabz Coin demo',
            published_at='2026-10-05T07:00:00+00:00', demo=True)]


def match_coins(text, coins):
    # Names only; ambiguous tickers such as ONE, GAS and duplicate symbols are deliberately excluded.
    return [coin['id'] for coin in coins if re.search(r'(?<!\w)' + re.escape(coin['name']) + r'(?!\w)', text, re.I)]


def ingest(store, articles, model=None, prompt_version='v1'):
    model = model or ('demo-fixture-v1' if store.settings.mode == 'demo' else 'pending-provider')
    cached = store.get('market')
    coins = cached[0] if cached else []
    count = 0
    for article in articles:
        # Separate namespaces avoid showing fixtures from a live database.
        if bool(article.get('demo')) != (store.settings.mode == 'demo'):
            raise ValueError('News mode mismatch')
        title, summary = clean(article['title']), clean(article.get('summary', ''))
        if not title:
            continue
        url = safe_url(article['url'], {urlsplit(article['url']).hostname})
        published = datetime.fromisoformat(article['published_at'])
        if published.tzinfo is None:
            raise ValueError('News timestamps must contain timezone')
        digest = hashlib.sha256(json.dumps([title, summary], ensure_ascii=False).encode()).hexdigest()
        identity = hashlib.sha256(url.encode()).hexdigest()
        with store.connection() as db:
            db.execute('INSERT INTO articles VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(url) DO UPDATE SET '
                'title_original=excluded.title_original,summary_original=excluded.summary_original,input_hash=excluded.input_hash,coin_ids=excluded.coin_ids',
                (identity, url, article['publisher'], title, summary, published.astimezone(timezone.utc).isoformat(),
                 digest, json.dumps(match_coins(title + ' ' + summary, coins)), int(article.get('demo', False))))
            db.execute('INSERT OR IGNORE INTO article_versions VALUES(?,?,?,?,?)',
                (identity, digest, title, summary, now_iso()))
            result = db.execute("INSERT OR IGNORE INTO translations(article_id,input_hash,model,prompt_version,status) VALUES(?,?,?,?,'pending')", (identity, digest, model, prompt_version))
            count += result.rowcount
    return count


class Translation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title_fa: str = Field(min_length=1, max_length=1000)
    summary_fa: str = Field(max_length=5000)


class TranslationProvider(Protocol):
    model: str
    def translate(self, title: str, summary: str) -> Translation: ...


class DemoTranslationProvider:
    model = 'demo-fixture-v1'
    prompt_version = 'v1'
    demo = True
    def translate(self, title, summary):
        if title != 'Demo: Bitcoin market guide 2026' or summary != 'Sample data only; price is 62450.25 USD.':
            raise ValueError('Demo translator supports only its exact fixture')
        return Translation(title_fa='دمو: راهنمای بازار بیت‌کوین 2026', summary_fa='فقط داده نمونه؛ قیمت 62450.25 USD است.')


class PersianNewsProvider:
    """Publish already-Persian feed text without calling a translation service."""
    model = 'persian-source-v1'
    prompt_version = 'v1'
    demo = False

    def translate(self, title, summary):
        translated = Translation(title_fa=title, summary_fa=summary)
        validate_translation(title, summary, translated)
        return translated


def validate_translation(title, summary, translated):
    result = translated.title_fa + ' ' + translated.summary_fa
    original = title + ' ' + summary
    numeral = r'[+-]?\d+(?:[.,]\d+)*(?:%)?'
    if sorted(re.findall(numeral, original)) != sorted(re.findall(numeral, result)):
        raise ValueError('Translation changed numbers, percentages or signs')
    symbols = re.findall(r'\b[A-Z][A-Z0-9]{1,9}\b', original)
    if any(not re.search(r'\b' + re.escape(s) + r'\b', result) for s in symbols):
        raise ValueError('Translation lost a symbol')
    if not summary and translated.summary_fa:
        raise ValueError('Translation invented a summary')
    if not re.search(r'[\u0600-\u06ff]', translated.title_fa):
        raise ValueError('Title is not Persian')
    if summary and not re.search(r'[\u0600-\u06ff]', translated.summary_fa):
        raise ValueError('Summary is not Persian')


def enqueue_current(store, provider):
    with store.connection() as db:
        db.execute("INSERT OR IGNORE INTO translations(article_id,input_hash,model,prompt_version,status) "
            "SELECT id,input_hash,?,?,'pending' FROM articles WHERE demo=?", (provider.model,
            getattr(provider, 'prompt_version', 'v1'), int(store.settings.mode == 'demo')))


def translate_one(store, provider):
    from .translation import TranslationUnavailable
    owner, now, day = uuid.uuid4().hex, time.time(), now_iso()[:10]
    with store.connection() as db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT t.*,a.title_original,a.summary_original,a.demo FROM translations t JOIN articles a '
            'ON t.article_id=a.id AND t.input_hash=a.input_hash '
            "WHERE t.model=? AND t.prompt_version=? AND t.status='pending' AND t.attempts<3 AND t.next_due<=? AND t.expires_at<=? LIMIT 1", (provider.model, getattr(provider, 'prompt_version', 'v1'), now, now)).fetchone()
        if row is None:
            return False
        if bool(row['demo']) != bool(getattr(provider, 'demo', True)):
            raise ValueError('Translation provider mode mismatch')
        disabled = db.execute("SELECT value FROM settings WHERE key=?", ('disabled:' + provider.model,)).fetchone()
        if disabled:
            return False
        usage = db.execute('SELECT count FROM translation_usage WHERE day=?', (day,)).fetchone()
        if usage and usage['count'] >= store.settings.translation_daily_limit:
            return False
        db.execute('INSERT INTO translation_usage VALUES(?,1) ON CONFLICT(day) DO UPDATE SET count=count+1', (day,))
        db.execute('UPDATE translations SET owner=?,expires_at=?,attempts=attempts+1 WHERE article_id=? AND input_hash=? AND model=? AND prompt_version=?',
            (owner, now+120, row['article_id'], row['input_hash'], row['model'], row['prompt_version']))
    try:
        translated = provider.translate(row['title_original'], row['summary_original'])
        translated = Translation.model_validate(translated)
        # Preserve numeric values and do not invent summary when no summary exists.
        validate_translation(row['title_original'], row['summary_original'], translated)
        with store.connection() as db:
            db.execute("UPDATE translations SET title_fa=?,summary_fa=?,status='ready',expires_at=0,owner=NULL WHERE owner=?",
                (translated.title_fa, translated.summary_fa, owner))
    except BudgetExceeded:
        with store.connection() as db:
            db.execute("UPDATE translations SET attempts=attempts-1,next_due=?,expires_at=0,owner=NULL WHERE owner=?", (now+3600, owner))
            db.execute('UPDATE translation_usage SET count=MAX(0,count-1) WHERE day=?', (day,))
        return False
    except TranslationUnavailable:
        with store.connection() as db:
            db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', ('disabled:' + provider.model, now_iso()))
            db.execute("UPDATE translations SET status='unavailable',expires_at=0,owner=NULL WHERE owner=?", (owner,))
        return False
    except Exception:
        with store.connection() as db:
            db.execute("UPDATE translations SET status='pending',next_due=?,expires_at=0,owner=NULL WHERE owner=?", (now+60, owner))
    return True
