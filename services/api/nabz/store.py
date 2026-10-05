from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sqlite3
import time
import uuid


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class BudgetExceeded(Exception):
    pass


class Store:
    """SQLite repository. Transactions serialize leases and credit reservations."""
    def __init__(self, settings):
        self.settings = settings
        Path(settings.database).parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute('PRAGMA journal_mode=WAL')
            for migration in sorted((Path(__file__).parent / 'migrations').glob('*.sql')):
                db.executescript(migration.read_text())
            row = db.execute("SELECT value FROM settings WHERE key='mode'").fetchone()
            if row and row['value'] != settings.mode:
                raise ValueError('Demo and live require separate databases')
            db.execute("INSERT OR IGNORE INTO settings VALUES('mode',?)", (settings.mode,))

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.settings.database, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def put(self, key, payload, fetched_at=None):
        with self.connection() as db:
            db.execute('INSERT OR REPLACE INTO cache VALUES(?,?,?)',
                (key, json.dumps(payload, allow_nan=False), fetched_at or now_iso()))

    def get(self, key):
        with self.connection() as db:
            row = db.execute('SELECT * FROM cache WHERE key=?', (key,)).fetchone()
        return (json.loads(row['payload']), row['fetched_at']) if row else None

    def snapshot_prices(self, coins, fetched_at=None):
        fetched_at = fetched_at or now_iso()
        cutoff = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        with self.connection() as db:
            db.executemany('INSERT OR IGNORE INTO market_snapshots VALUES(?,?,?)',
                [(c['id'], fetched_at, c['price']) for c in coins])
            db.execute('DELETE FROM market_snapshots WHERE time<?', (cutoff,))

    def price_history(self, cmc_id, days):
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self.connection() as db:
            rows = db.execute('SELECT time,price FROM market_snapshots WHERE cmc_id=? AND time>=? ORDER BY time',
                (cmc_id, cutoff)).fetchall()
        # Even sampling retains first/last and original chronological order.
        if len(rows) > 250:
            rows = [rows[round(i * (len(rows)-1) / 249)] for i in range(250)]
        return [dict(row) for row in rows]

    def put_metadata(self, entries, fetched_at):
        with self.connection() as db:
            db.executemany('INSERT OR REPLACE INTO coin_metadata VALUES(?,?,?)',
                [(int(i), json.dumps(v), fetched_at) for i, v in entries.items()])

    def enrich_coins(self, coins):
        with self.connection() as db:
            metadata = {row['cmc_id']: json.loads(row['payload']) for row in db.execute('SELECT * FROM coin_metadata')}
        return [{**c, **metadata.get(c['id'], {})} for c in coins]

    def acquire_job(self, name, interval, ttl=180):
        owner, now = uuid.uuid4().hex, time.time()
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            due = db.execute('SELECT next_due,status FROM job_status WHERE name=?', (name,)).fetchone()
            if due and (due['next_due'] > now or due['status'] == 'unavailable'):
                return None
            lock = db.execute('SELECT expires_at FROM job_locks WHERE name=?', (name,)).fetchone()
            if lock and lock['expires_at'] > now:
                return None
            db.execute('INSERT OR REPLACE INTO job_locks VALUES(?,?,?)', (name, owner, now + ttl))
        return owner

    def finish_job(self, name, owner, interval, status='ready'):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT owner FROM job_locks WHERE name=?', (name,)).fetchone()
            if not row or row['owner'] != owner:
                return
            db.execute('INSERT OR REPLACE INTO job_status VALUES(?,?,?)', (name, time.time() + interval, status))
            db.execute('DELETE FROM job_locks WHERE name=? AND owner=?', (name, owner))

    def reserve(self, category, estimate=1):
        if not isinstance(estimate, int) or isinstance(estimate, bool) or estimate <= 0:
            raise ValueError('Credit estimate must be a positive integer')
        month = now_iso()[:7]
        token = uuid.uuid4().hex
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            used = db.execute('SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM usage_records WHERE month=?', (month,)).fetchone()[0]
            if used + estimate + self.settings.external_credits > self.settings.monthly_limit:
                raise BudgetExceeded('Monthly credit budget reached')
            cap = {'history': self.settings.history_limit, 'metadata': self.settings.metadata_limit}.get(category)
            if cap is not None:
                subtotal = db.execute('SELECT COALESCE(SUM(COALESCE(actual,reserved)),0) FROM usage_records WHERE month=? AND category=?',
                    (month, category)).fetchone()[0]
                if subtotal + estimate > cap:
                    raise BudgetExceeded('Optional category budget reached')
            db.execute('INSERT INTO usage_records VALUES(?,?,?,?,NULL,?)', (token, month, category, estimate, now_iso()))
        return token

    def settle(self, token, actual):
        if not isinstance(actual, int) or isinstance(actual, bool) or actual < 0:
            raise ValueError('Invalid upstream credit_count')
        with self.connection() as db:
            db.execute('UPDATE usage_records SET actual=? WHERE id=?', (actual, token))

    def reserve_translation_cost(self, model, estimate, daily_limit):
        if estimate <= 0 or daily_limit <= 0:
            raise ValueError('Translation cost limits must be positive')
        day, token = now_iso()[:10], uuid.uuid4().hex
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            used = db.execute('SELECT COALESCE(SUM(COALESCE(actual_microusd,reserved_microusd)),0) '
                'FROM translation_costs WHERE day=?', (day,)).fetchone()[0]
            if used + estimate > daily_limit:
                raise BudgetExceeded('Daily translation cost budget reached')
            db.execute('INSERT INTO translation_costs VALUES(?,?,?,NULL,?,NULL,NULL,?)',
                (token, day, estimate, model, now_iso()))
        return token

    def settle_translation_cost(self, token, actual, input_tokens, output_tokens):
        with self.connection() as db:
            db.execute('UPDATE translation_costs SET actual_microusd=?,input_tokens=?,output_tokens=? WHERE id=?',
                (actual, input_tokens, output_tokens, token))

    def rate_allowed(self, client, limit=60):
        minute = int(time.time() // 60)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM rate_limits WHERE minute<?', (minute - 2,))
            db.execute('INSERT INTO rate_limits VALUES(?,?,1) ON CONFLICT(client,minute) DO UPDATE SET count=count+1', (client, minute))
            return db.execute('SELECT count FROM rate_limits WHERE client=? AND minute=?', (client, minute)).fetchone()[0] <= limit
