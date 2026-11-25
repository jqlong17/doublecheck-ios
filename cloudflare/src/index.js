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

const HTML = (stats, recent, actions) => {
  const counts = Object.fromEntries(stats.byAction.map((r) => [r.action, r]))
  const PLATFORMS = { ios: "iOS", linux: "Linux / systemd", net: "网络 / TLS" }
  const STAGES = { commit: "提交前", build: "构建", test: "测试", release: "发版", operate: "运行时" }
  const domains = {}
  for (const a of actions) {
    domains[a.platform] = domains[a.platform] || {}
    const st = a.stage || "operate"
    ;(domains[a.platform][st] = domains[a.platform][st] || []).push(a)
  }

  const KIND = { invariant: ["●", "不变式"], policy: ["◇", "策略"], diagnostic: ["○", "诊断"] }
  const actionRows = (list) => list.map((a) => {
    const [sym, label] = KIND[a.kind] || ["?", a.kind]
    const AREA = { project: "工程", connection: "连接", message: "消息", conversation: "对话", settings: "设置", plugin: "插件", system: "系统" }
    const areaTag = a.area && a.area !== "project" ? ` <span class="kind">${AREA[a.area] || a.area}</span>` : ""
    const c = counts[a.id]
    const badge = c ? `<span class="pill ${c.fail ? "bad" : "ok"}">${c.total} 次${c.fail ? " · " + c.fail + " 失败" : ""}</span>` : `<span class="pill">未运行</span>`
    return `<tr><td><div class="mono">${a.id} <span class="kind" title="${label}">${sym} ${label}</span>${areaTag}</div><div class="sub">${a.summary || ""}</div></td><td style="text-align:right;white-space:nowrap">${badge}</td></tr>`
  }).join("") || '<tr><td class="muted">暂无</td></tr>'

  const sections = Object.entries(domains).map(([d, byStage]) => {
    const total = Object.values(byStage).reduce((n, l) => n + l.length, 0)
    const inner = Object.entries(byStage).map(([st, list]) =>
      `<h2>${PLATFORMS[d] || d} · ${STAGES[st] || st} <span class="muted">· ${list.length}</span></h2><table>${actionRows(list)}</table>`
    ).join("")
    return `<h1 style="margin-top:28px">${PLATFORMS[d] || d} <span class="muted">· ${total}</span></h1>${inner}`
  }).join("")

  return `<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>doublecheck 管理端</title>
<style>
  :root{--bg:#0b0f14;--card:#151b23;--fg:#e8eef6;--dim:#8b98a8;--ok:#3ddc84;--bad:#ff5c5c}
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;padding:16px 16px 40px}
  h1{font-size:20px;margin:4px 0 6px}
  .muted{color:var(--dim);font-size:13px}
  .grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:16px 0}
  .card{background:var(--card);border-radius:14px;padding:14px}
  .num{font-size:26px;font-weight:600;margin-top:4px}
  .ok{color:var(--ok)} .bad{color:var(--bad)}
  h2{font-size:14px;margin:22px 0 8px;color:var(--dim);font-weight:500}
  table{width:100%;border-collapse:collapse;background:var(--card);border-radius:14px;overflow:hidden}
  td{padding:11px 12px;vertical-align:top;border-bottom:1px solid #1f2733;font-size:14px}
  tr:last-child td{border-bottom:none}
  .mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px}
  .sub{color:var(--dim);font-size:13px;margin-top:3px;line-height:1.45}
  .kind{font-size:11px;color:var(--dim);border:1px solid #2a3442;border-radius:6px;padding:1px 5px;margin-left:4px}
  .pill{display:inline-block;background:#1f2733;color:var(--dim);border-radius:999px;padding:3px 9px;font-size:12px}
  .pill.ok{background:rgba(61,220,132,.14);color:var(--ok)}
  .pill.bad{background:rgba(255,92,92,.14);color:var(--bad)}
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;vertical-align:middle}
</style></head><body>
<h1>doublecheck 管理端</h1>
<div class="muted">刷新 ${new Date(stats.now).toLocaleString("zh-CN", { timeZone: "Asia/Shanghai" })} · 30 秒自动刷新</div>

<div class="grid">
  <div class="card"><div class="muted">总调用</div><div class="num">${stats.total}</div></div>
  <div class="card"><div class="muted">成功率</div><div class="num ${stats.okRate >= 0.9 ? "ok" : "bad"}">${stats.okRate == null ? "—" : Math.round(stats.okRate * 100) + "%"}</div></div>
  <div class="card"><div class="muted">今日</div><div class="num">${stats.today}</div></div>
  <div class="card"><div class="muted">动作库</div><div class="num">${actions.length}</div></div>
</div>

${sections}

<h2>工具分布</h2>
<table>${stats.byTool.map((r) => `<tr><td>${r.tool ?? "?"}</td><td style="text-align:right" class="muted">${r.total} 次</td></tr>`).join("") || '<tr><td class="muted">还没有数据</td></tr>'}</table>

<h2>最近 20 条</h2>
<table>${recent.map((r) => `<tr><td class="mono">${String(r.ts).replace("T", " ").replace("Z", "").slice(5, 16)}</td><td class="mono">${r.action}</td><td style="text-align:right">${r.ok ? '<span class="dot" style="background:var(--ok)"></span>成功' : '<span class="dot" style="background:var(--bad)"></span>失败'}</td></tr>`).join("") || '<tr><td class="muted">还没有数据</td></tr>'}</table>

<p class="muted" style="margin-top:24px">只统计 tool / action / ok / agent 四个字段，不含主机名与输出。</p>
<script>setTimeout(()=>location.reload(), 30000)</script>
</body></html>`
}

async function listActions(env) {
  const r = await env.DB.prepare("SELECT id, platform, version, sha256, updated_at FROM actions ORDER BY domain, id").all()
  return r.results || []
}

async function getAction(env, id) {
  return env.DB.prepare("SELECT id, domain, version, yaml, sha256 FROM actions WHERE id = ?").bind(id).first()
}

async function putAction(env, a) {
  const now = new Date().toISOString()
  await env.DB.prepare(
    `INSERT INTO actions (id, platform, version, yaml, sha256, signature, summary, kind, stage, area, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)
     ON CONFLICT(id) DO UPDATE SET platform=excluded.platform, version=excluded.version,
       yaml=excluded.yaml, sha256=excluded.sha256, signature=excluded.signature,
       summary=excluded.summary, kind=excluded.kind, stage=excluded.stage,
       area=excluded.area, updated_at=excluded.updated_at`
  ).bind(a.id, a.platform, a.version, a.yaml, a.sha256, a.signature || null, a.summary || null,
         a.kind || "invariant", a.stage || "operate", a.area || "project", now).run()
  return now
}

async function verifySignature(pubPem, yaml, signatureB64) {
  try {
    // 支持两种存法：PEM（带 ----- 标记）或单行 base64 DER
    const b64 = pubPem.includes("-----")
      ? pubPem.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "")
      : pubPem.replace(/\s+/g, "")
    const raw = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0))
    // SPKI 头 12 字节后是 32 字节原始公钥
    const key = await crypto.subtle.importKey("raw", raw.slice(12), { name: "Ed25519" }, false, ["verify"])
    return await crypto.subtle.verify("Ed25519", key, Uint8Array.from(atob(signatureB64), (c) => c.charCodeAt(0)), new TextEncoder().encode(yaml))
  } catch {
    return false
  }
}

async function stats(env) {
  const byAction = await env.DB.prepare(
    "SELECT action, SUM(ok) AS ok, SUM(1-ok) AS fail, COUNT(*) AS total FROM events GROUP BY action ORDER BY total DESC LIMIT 50"
  ).all()
  const byTool = await env.DB.prepare(
    "SELECT tool, COUNT(*) AS total FROM events GROUP BY tool ORDER BY total DESC"
  ).all()
  const total = await env.DB.prepare("SELECT COUNT(*) AS total, SUM(ok) AS ok FROM events").first()
  const act = await env.DB.prepare("SELECT COUNT(*) AS n FROM actions").first()
  const today = await env.DB.prepare(
    "SELECT COUNT(*) AS n FROM events WHERE date(received_at) = date('now')"
  ).first()
  return {
    now: Date.now(),
    total: total?.total ?? 0,
    okRate: total?.total ? total.ok / total.total : null,
    today: today?.n ?? 0,
    actions: act?.n ?? 0,
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

    if (url.pathname === "/v1/actions" && request.method === "GET") {
      // ?full=1 一次返回全部 YAML：国内到 CF 的往返很贵，14 个请求会超时
      if (url.searchParams.get("full") === "1") {
        const r = await env.DB.prepare("SELECT id, platform, version, yaml, sha256, signature FROM actions ORDER BY domain, id").all()
        return json(200, { actions: r.results || [] })
      }
      return json(200, { actions: await listActions(env) })
    }

    if (url.pathname.startsWith("/v1/actions/") && request.method === "GET") {
      const id = decodeURIComponent(url.pathname.slice("/v1/actions/".length))
      const a = await getAction(env, id)
      return a ? json(200, a) : json(404, { error: "action not found" })
    }

    if (url.pathname === "/v1/actions" && request.method === "POST") {
      // 只允许用 meta 表里的 push_token 推送，避免任何人改库
      const token = (request.headers.get("authorization") || "").replace("Bearer ", "")
      const expect = await env.DB.prepare("SELECT value FROM meta WHERE key='push_token'").first()
      if (!expect?.value || token !== expect.value) return json(401, { error: "unauthorized" })
      let b
      try { b = await request.json() } catch { return json(400, { error: "invalid json" }) }
      const items = Array.isArray(b) ? b : [b]
      const pubRow = await env.DB.prepare("SELECT value FROM meta WHERE key='pubkey'").first()
      if (!pubRow?.value) return json(500, { error: "registry pubkey not configured" })
      let n = 0
      const rejected = []
      for (const a of items) {
        if (!a.id || !a.yaml || !a.sha256 || !a.signature) { rejected.push(a.id || "?"); continue }
        const ok = await verifySignature(pubRow.value, a.yaml, a.signature)
        if (!ok) { rejected.push(a.id); continue }
        await putAction(env, a)
        n++
      }
      return json(200, { accepted: n, rejected })
    }

    if (url.pathname === "/v1/recent") {
      const r = await env.DB.prepare(
        "SELECT ts, action, tool, ok FROM events ORDER BY id DESC LIMIT 20"
      ).all()
      return json(200, { events: r.results || [] })
    }

    if (url.pathname === "/" || url.pathname === "/index.html") {
      const s = await stats(env)
      const r = await env.DB.prepare("SELECT ts, action, ok FROM events ORDER BY id DESC LIMIT 20").all()
      const a = await env.DB.prepare("SELECT id, platform, summary, kind, stage, area FROM actions ORDER BY platform, stage, id").all()
      return new Response(HTML(s, r.results || [], a.results || []), {
        headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
      })
    }

    return json(404, { error: "not found" })
  },
}
