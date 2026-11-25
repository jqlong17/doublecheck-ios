CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,            -- 客户端时间（UTC ISO8601）
  received_at TEXT NOT NULL,   -- 服务端接收时间
  tool TEXT,                   -- plan / call / verify
  action TEXT NOT NULL,        -- 动作 id
  ok INTEGER NOT NULL,         -- 1 成功 / 0 失败
  agent TEXT,                  -- 匿名标识（不做用户画像）
  version TEXT
);
CREATE INDEX IF NOT EXISTS idx_events_action ON events(action);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
