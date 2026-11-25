/**
 * doublecheck 用量统计 Worker + 管理端。
 *
 *   GET  /            管理端（手机可直接打开）
 *   GET  /v1/stats    聚合统计
 *   GET  /v1/recent   最近事件
 *   POST /v1/events   写入一条事件
 *
 * 只存「谁在什么动作上、成功还是失败」，不存主机名、路径、输出。
 */

const HTML = (stats, recent) => `<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>doublecheck 管理端</title>
<style>
  :root{--bg:#0b0f14;--card:#151b23;--fg:#e8eef6;--dim:#8b98a8;--ok:#3ddc84;--bad:#ff5c5c;--accent:#5aa9ff}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;padding:16px 16px 40px}
  h1{font-size:20px;margin:4px 0 16px}
  .muted{color:var(--dim);font-size:13px}
  .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:16px}
  .card{background:var(--card);border-radius:14px;padding:14px}
  .num{font-size:26px;font-weight:600;margin-top:4px}
  .ok{color:var(--ok)} .bad{color:var(--bad)}
  h2{font-size:15px;margin:20px 0 8px;color:var(--dim);font-weight:500}
  table{width:100%;border-collapse:collapse;background:var(--card);border-radius:14px;overflow:hidden}
  td,th{padding:10px 12px;text-align:left;font-size:14px;border-bottom:1px solid #1f2733}
  th{color:var(--dim);font-weight:500;font-size:12px}
  tr:last-child td{border-bottom:none}
  .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}
</style></head><body>
<h1>doublecheck 管理端</h1>
<div class="muted">最近刷新 ${new Date(stats.now).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" })} · 每 30 秒自动刷新</div>

<div class="grid">
  <div class="card"><div class="muted">总调用</div><div class="num">${stats.total}</div></div>
  <div class="card"><div class="muted">成功率</div><div class="num ${stats.okRate >= 0.9 ? "ok" : "bad"}">${stats.okRate == null ? "—" : Math.round(stats.okRate * 100) + "%"}</div></div>
  <div class="card"><div class="muted">今日</div><div class="num">${stats.today}</div></div>
  <div class="card"><div class="muted">覆盖动作</div><div class="num">${stats.byAction.length}</div></div>
</div>

<h2>按动作</h2>
<table><tr><th>动作</th><th>成功</th><th>失败</th><th>合计</th></tr>
${stats.byAction.map((r) => `<tr><td class="mono">${r.action}</td><td class="ok">${r.ok ?? 0}</td><td class="bad">${r.fail ?? 0}</td><td>${r.total}</td></tr>`).join("") || '<tr><td colspan="4" class="muted">还没有数据</td></tr>'}
</table>

<h2>按工具</h2>
<table><tr><th>工具</th><th>次数</th></tr>
${stats.byTool.map((r) => `<tr><td>${r.tool ?? "?"}</td><td>${r.total}</td></tr>`).join("") || '<tr><td colspan="2" class="muted">还没有数据</td></tr>'}
</table>

<h2>最近 20 条</h2>
<table><tr><th>时间</th><th>动作</th><th>结果</th></tr>
${recent.map((r) => `<tr><td class="mono">${String(r.ts).replace("T", " ").replace("Z", "").slice(5, 16)}</td><td class="mono">${r.action}</td><td>${r.ok ? '<span class="dot" style="background:var(--ok)"></span>成功' : '<span class="dot" style="background:var(--bad)"></span>失败'}</td></tr>`).join("") || '<tr><td colspan="3" class="muted">还没有数据</td></tr>'}
</table>

<p class="muted" style="margin-top:24px">只统计 tool / action / ok / agent 四个字段，不含主机名与输出。</p>
<script>setTimeout(()=>location.reload(), 30000)</script>
</body></html>`

async function stats(env) {
  const byAction = await env.DB.prepare(
    "SELECT action, SUM(ok) AS ok, SUM(1-ok) AS fail, COUNT(*) AS total FROM events GROUP BY action ORDER BY total DESC LIMIT 50"
  ).all()
  const byTool = await env.DB.prepare(
    "SELECT tool, COUNT(*) AS total FROM events GROUP BY tool ORDER BY total DESC"
  ).all()
  const total = await env.DB.prepare("SELECT COUNT(*) AS total, SUM(ok) AS ok FROM events").first()
  const today = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM events WHERE date(received_at) = date('now')"
  ).first()
  return {
    now: Date.now(),
    total: total?.total ?? 0,
    okRate: total?.total ? total.ok / total.total : null,
    today: today?.n ?? 0,
    byAction: byAction.results || [],
    byTool: byTool.results || [],
  }
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url)
    const json = (code, obj) =>
      new Response(JSON.stringify(obj), { status: code, headers: { "content-type": "application/json" } })

    if (request.method === "POST" && url.pathname === "/v1/events") {
      let d
      try { d = await request.json() } catch { return json(400, { error: "invalid json" }) }
      if (!d.action) return json(400, { error: "action required" })
      await env.DB.prepare(
        "INSERT INTO events (ts, received_at, tool, action, ok, agent, version) VALUES (?,?,?,?,?,?,?)"
      ).bind(
        d.ts || new Date().toISOString(), new Date().toISOString(),
        d.tool || null, d.action, d.ok ? 1 : 0, d.agent || null, d.version || null
      ).run()
      return json(200, { ok: true })
    }

    if (url.pathname === "/v1/stats") return json(200, await stats(env))

    if (url.pathname === "/v1/recent") {
      const r = await env.DB.prepare(
        "SELECT ts, action, tool, ok FROM events ORDER BY id DESC LIMIT 20"
      ).all()
      return json(200, { events: r.results || [] })
    }

    if (url.pathname === "/" || url.pathname === "/index.html") {
      const s = await stats(env)
      const r = await env.DB.prepare("SELECT ts, action, ok FROM events ORDER BY id DESC LIMIT 20").all()
      return new Response(HTML(s, r.results || []), {
        headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
      })
    }

    return json(404, { error: "not found" })
  },
}
