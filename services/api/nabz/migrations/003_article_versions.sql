CREATE TABLE IF NOT EXISTS article_versions(article_id TEXT NOT NULL, input_hash TEXT NOT NULL,
  title_original TEXT NOT NULL, summary_original TEXT NOT NULL, received_at TEXT NOT NULL,
  PRIMARY KEY(article_id,input_hash));
INSERT OR IGNORE INTO article_versions SELECT id,input_hash,title_original,summary_original,published_at FROM articles;
CREATE INDEX IF NOT EXISTS news_date_cursor ON articles(published_at DESC,id DESC);
INSERT OR IGNORE INTO schema_version VALUES(3);
