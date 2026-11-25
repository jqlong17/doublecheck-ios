/**
 * doublecheck 用量统计 Worker。
 *
 * 只存「谁在什么动作上、成功还是失败」，不存主机名、路径、输出。
 *   POST /v1/events  {ts,tool,action,ok,agent,version}
 *   GET  /v1/stats   按 action / tool 聚合
 */
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
        d.ts || new Date().toISOString(),
        new Date().toISOString(),
        d.tool || null,
        d.action,
        d.ok ? 1 : 0,
        d.agent || null,
        d.version || null
      ).run()
      return json(200, { ok: true })
    }

    if (request.method === "GET" && url.pathname === "/v1/stats") {
      const byAction = await env.DB.prepare(
        "SELECT action, SUM(ok) AS ok, SUM(1-ok) AS fail, COUNT(*) AS total FROM events GROUP BY action ORDER BY total DESC LIMIT 100"
      ).all()
      const byTool = await env.DB.prepare(
        "SELECT tool, COUNT(*) AS total FROM events GROUP BY tool"
      ).all()
      const total = await env.DB.prepare("SELECT COUNT(*) AS total, SUM(ok) AS ok FROM events").first()
      return json(200, {
        total: total?.total ?? 0,
        okRate: total?.total ? +(total.ok / total.total).toFixed(3) : null,
        byAction: byAction.results,
        byTool: byTool.results,
      })
    }

    return json(404, { error: "not found" })
  },
}
