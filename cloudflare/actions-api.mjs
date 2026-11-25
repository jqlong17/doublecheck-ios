// 动作分发相关的代码片段（由 src/index.js 引入，保持 Worker 单文件可部署）
export async function listActions(env) {
  const r = await env.DB.prepare(
    "SELECT id, domain, version, sha256, updated_at FROM actions ORDER BY domain, id"
  ).all()
  return r.results || []
}

export async function getAction(env, id) {
  return env.DB.prepare("SELECT id, domain, version, yaml, sha256 FROM actions WHERE id = ?").bind(id).first()
}

export async function putAction(env, payload) {
  const now = new Date().toISOString()
  await env.DB.prepare(
    `INSERT INTO actions (id, domain, version, yaml, sha256, updated_at) VALUES (?,?,?,?,?,?)
     ON CONFLICT(id) DO UPDATE SET domain=excluded.domain, version=excluded.version,
       yaml=excluded.yaml, sha256=excluded.sha256, updated_at=excluded.updated_at`
  ).bind(payload.id, payload.domain, payload.version, payload.yaml, payload.sha256, now).run()
  return now
}

export async function pushToken(env) {
  const row = await env.DB.prepare("SELECT value FROM meta WHERE key = 'push_token'").first()
  return row?.value || null
}
