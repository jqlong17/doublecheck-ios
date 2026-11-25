CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  received_at TEXT NOT NULL,
  tool TEXT,
  action TEXT NOT NULL,
  ok INTEGER NOT NULL,
  agent TEXT,
  version TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_action ON events(action);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);

CREATE TABLE IF NOT EXISTS actions (
  id TEXT PRIMARY KEY,          -- 例如 ios.pbxproj-registered
  domain TEXT NOT NULL,         -- ios / linux / net
  version TEXT NOT NULL,
  yaml TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_actions_domain ON actions(domain);

CREATE TABLE IF NOT EXISTS meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
