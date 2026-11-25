#!/usr/bin/env node
/**
 * dash —— 中央服务的最小实现（本地验证用，之后平移到 Cloudflare Workers + D1）
 *
 *   GET  /v1/actions        列出已发布动作
 *   POST /v1/evidence       接收证据（每行一个 JSON）
 *   POST /v1/submissions    接收动作提交
 *   GET  /v1/stats          简单的聚合视图
 *
 * 启动：node dash.mjs [port]   （默认 8790）
 * 数据：~/.doublecheck/dash/{evidence.jsonl,submissions/}
 */
import { createServer } from "node:http"
import { appendFileSync, mkdirSync, readdirSync, readFileSync, writeFileSync, existsSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

const PORT = Number(process.argv[2] || 8790)
const HOME = join(homedir(), ".doublecheck", "dash")
const EVIDENCE = join(HOME, "evidence.jsonl")
const SUBS = join(HOME, "submissions")
mkdirSync(SUBS, { recursive: true })

function body(req) {
  return new Promise((resolve) => {
    let b = ""
    req.on("data", (d) => (b += d))
    req.on("end", () => resolve(b))
  })
}

function actionsIndex() {
  const root = join(import.meta.dirname, "..", "actions")
  if (!existsSync(root)) return []
  const files = []
  for (const dom of readdirSync(root)) {
    const dir = join(root, dom)
    if (!existsSync(dir)) continue
    for (const f of readdirSync(dir)) if (f.endsWith(".yaml")) files.push([dom, join(dir, f)])
  }
  return files.map(([dom, path]) => {
    const f = path
    const text = readFileSync(path, "utf8")
    const id = (text.match(/^action:\s*(\S+)/m) || [])[1] || f
    const summary = (text.match(/^summary:\s*(.+)$/m) || [])[1] || ""
    return { id, domain: dom, summary, version: "0.1.0", status: "verified" }
  })
}

function stats() {
  if (!existsSync(EVIDENCE)) return { total: 0, byAction: {} }
  const byAction = {}
  let total = 0
  for (const line of readFileSync(EVIDENCE, "utf8").split("\n")) {
    if (!line.trim()) continue
    let d
    try { d = JSON.parse(line) } catch { continue }
    total++
    const k = d.action || "?"
    byAction[k] = byAction[k] || { ok: 0, fail: 0 }
    d.ok ? byAction[k].ok++ : byAction[k].fail++
  }
  return { total, byAction }
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`)
  const json = (code, obj) => {
    res.writeHead(code, { "content-type": "application/json" })
    res.end(JSON.stringify(obj))
  }

  if (req.method === "GET" && url.pathname === "/v1/actions") {
    return json(200, { actions: actionsIndex() })
  }
  if (req.method === "GET" && url.pathname === "/v1/stats") {
    return json(200, stats())
  }
  if (req.method === "POST" && url.pathname === "/v1/evidence") {
    const b = await body(req)
    const lines = b.split("\n").filter((l) => l.trim())
    for (const l of lines) {
      try { JSON.parse(l) } catch { return json(400, { error: "invalid ndjson line" }) }
    }
    appendFileSync(EVIDENCE, lines.join("\n") + "\n")
    return json(200, { accepted: lines.length })
  }
  if (req.method === "POST" && url.pathname === "/v1/submissions") {
    const b = await body(req)
    const name = `sub-${Date.now()}.yaml`
    writeFileSync(join(SUBS, name), b)
    return json(200, { id: name, status: "pending" })
  }
  json(404, { error: "not found" })
})

server.listen(PORT, "127.0.0.1", () => {
  console.log(`dash listening on http://127.0.0.1:${PORT}`)
})
