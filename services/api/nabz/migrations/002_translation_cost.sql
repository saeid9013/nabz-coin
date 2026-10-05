CREATE TABLE IF NOT EXISTS translation_costs(id TEXT PRIMARY KEY, day TEXT NOT NULL,
  reserved_microusd INTEGER NOT NULL, actual_microusd INTEGER, model TEXT NOT NULL,
  input_tokens INTEGER, output_tokens INTEGER, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS translation_cost_day ON translation_costs(day);
INSERT OR IGNORE INTO schema_version VALUES(2);
