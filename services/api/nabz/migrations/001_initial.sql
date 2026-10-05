CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version VALUES(1);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS market_snapshots(cmc_id INTEGER NOT NULL, time TEXT NOT NULL, price REAL NOT NULL,
  PRIMARY KEY(cmc_id,time));
CREATE TABLE IF NOT EXISTS coin_metadata(cmc_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, fetched_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS job_locks(name TEXT PRIMARY KEY, owner TEXT NOT NULL, expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS job_status(name TEXT PRIMARY KEY, next_due REAL NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS usage_records(id TEXT PRIMARY KEY, month TEXT NOT NULL, category TEXT NOT NULL,
  reserved INTEGER NOT NULL, actual INTEGER, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS usage_month ON usage_records(month);
CREATE TABLE IF NOT EXISTS rate_limits(client TEXT NOT NULL, minute INTEGER NOT NULL, count INTEGER NOT NULL,
  PRIMARY KEY(client,minute));
CREATE TABLE IF NOT EXISTS articles(id TEXT PRIMARY KEY, url TEXT NOT NULL UNIQUE, publisher TEXT NOT NULL,
  title_original TEXT NOT NULL, summary_original TEXT NOT NULL, published_at TEXT NOT NULL,
  input_hash TEXT NOT NULL, coin_ids TEXT NOT NULL, demo INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS translations(article_id TEXT NOT NULL, input_hash TEXT NOT NULL,
  model TEXT NOT NULL, prompt_version TEXT NOT NULL, title_fa TEXT, summary_fa TEXT,
  status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
  next_due REAL NOT NULL DEFAULT 0, owner TEXT, expires_at REAL NOT NULL DEFAULT 0,
  PRIMARY KEY(article_id,input_hash,model,prompt_version));
CREATE TABLE IF NOT EXISTS translation_usage(day TEXT PRIMARY KEY, count INTEGER NOT NULL);
