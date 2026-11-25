#!/usr/bin/env node
/**
 * doublecheck MCP server（stdio）
 *
 * 给任何支持 MCP 的客户端（Claude Code / Cursor / DSH …）暴露四个工具：
 *   dc_list      列出可用动作
 *   dc_plan      预检：现在能不能做、会执行什么
 *   dc_call      执行（默认演练，confirm=true 才真跑）
 *   dc_verify    复检：只跑后置断言
 *
 * 每次调用都会写一条证据到 ~/.doublecheck/evidence.jsonl（本地队列），
 * 之后由 dc sync 上报（默认关闭，需要 DASH_URL 环境变量）。
 *
 * 启动：node server.mjs
 * 客户端配置示例（Claude Code / Cursor 的 mcpServers）：
 *   "doublecheck": { "command": "node", "args": ["/root/ops/mcp/server.mjs"] }
 */
import { spawn } from "node:child_process"
import { appendFileSync, mkdirSync, readFileSync, existsSync } from "node:fs"
import { homedir } from "node:os"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const HERE = dirname(fileURLToPath(import.meta.url))
const OPS = join(HERE, "..", "ops.py")
const STATE_DIR = join(homedir(), ".doublecheck")
const EVIDENCE = join(STATE_DIR, "evidence.jsonl")

function log(rec) {
  try {
    mkdirSync(STATE_DIR, { recursive: true })
    appendFileSync(EVIDENCE, JSON.stringify({ ts: new Date().toISOString(), ...rec }) + "\n")
  } catch { /* 证据写失败不影响主流程 */ }
}

function runOps(args, timeoutMs = 120000) {
  return new Promise((resolve) => {
    const p = spawn("python3", [OPS, ...args], { stdio: ["ignore", "pipe", "pipe"] })
    let out = "", err = ""
    const timer = setTimeout(() => p.kill("SIGKILL"), timeoutMs)
    p.stdout.on("data", (d) => (out += d))
    p.stderr.on("data", (d) => (err += d))
    p.on("close", (code) => {
      clearTimeout(timer)
      resolve({ code, out: out.trim(), err: err.trim() })
    })
  })
}

const TOOLS = [
  {
    name: "dc_list",
    description: "列出本机可用的运维动作（带一句话说明和默认参数）。",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "dc_plan",
    description: "预检：评估一个动作的前置条件，并返回将要执行的步骤与回滚方案。不执行任何步骤。",
    inputSchema: {
      type: "object",
      properties: {
        action: { type: "string", description: "动作 id，例如 service.restart" },
        params: { type: "object", description: "参数覆盖，例如 {\"unit\":\"dsh-web.service\"}" },
      },
      required: ["action"],
    },
  },
  {
    name: "dc_call",
    description: "执行一个动作。默认演练（不真正执行）；confirm=true 才会执行步骤并跑后置断言。",
    inputSchema: {
      type: "object",
      properties: {
        action: { type: "string" },
        params: { type: "object" },
        confirm: { type: "boolean", description: "true 表示真的执行" },
      },
      required: ["action"],
    },
  },
  {
    name: "dc_verify",
    description: "只跑后置断言，确认某个动作的结果仍然成立。",
    inputSchema: {
      type: "object",
      properties: { action: { type: "string" }, params: { type: "object" } },
      required: ["action"],
    },
  },
]

function kvArgs(params = {}) {
  return Object.entries(params).map(([k, v]) => `${k}=${v}`)
}

async function handle(name, args) {
  if (name === "dc_list") {
    const r = await runOps(["list"])
    return { content: [{ type: "text", text: r.out || r.err }] }
  }
  if (name === "dc_plan" || name === "dc_verify") {
    const sub = name === "dc_plan" ? "plan" : "verify"
    const r = await runOps([sub, args.action, "--json", ...kvArgs(args.params)])
    let parsed = null
    try { parsed = JSON.parse(r.out) } catch { /* 非 JSON 就原样返回 */ }
    log({ tool: sub, action: args.action, ok: parsed ? parsed.ok : r.code === 0, params: args.params || {} })
    return {
      content: [{ type: "text", text: r.out || r.err }],
      isError: r.code !== 0,
    }
  }
  if (name === "dc_call") {
    const extra = args.confirm ? ["--yes"] : []
    const r = await runOps(["call", args.action, ...kvArgs(args.params), ...extra])
    log({ tool: "call", action: args.action, confirm: !!args.confirm, ok: r.code === 0, params: args.params || {} })
    return { content: [{ type: "text", text: r.out || r.err }], isError: r.code !== 0 }
  }
  throw new Error(`未知工具 ${name}`)
}

// ---------------- JSON-RPC ----------------
let buf = ""
process.stdin.setEncoding("utf8")
process.stdin.on("data", async (chunk) => {
  buf += chunk
  let idx
  while ((idx = buf.indexOf("\n")) >= 0) {
    const line = buf.slice(0, idx).trim()
    buf = buf.slice(idx + 1)
    if (!line) continue
    let msg
    try { msg = JSON.parse(line) } catch { continue }
    const reply = async () => {
      if (msg.method === "initialize") {
        return {
          jsonrpc: "2.0", id: msg.id,
          result: {
            protocolVersion: "2024-11-05",
            capabilities: { tools: {} },
            serverInfo: { name: "doublecheck", version: "0.1.0" },
            instructions:
              "在执行任何运维操作前，先用 dc_plan 确认前置条件；执行后用 dc_verify 复检。" +
              "不要跳过 plan 直接 call。",
          },
        }
      }
      if (msg.method === "tools/list") {
        return { jsonrpc: "2.0", id: msg.id, result: { tools: TOOLS } }
      }
      if (msg.method === "tools/call") {
        try {
          const res = await handle(msg.params.name, msg.params.arguments || {})
          return { jsonrpc: "2.0", id: msg.id, result: res }
        } catch (e) {
          return { jsonrpc: "2.0", id: msg.id, result: { content: [{ type: "text", text: String(e) }], isError: true } }
        }
      }
      if (msg.method && msg.id === undefined) return null   // 通知，不回复
      return { jsonrpc: "2.0", id: msg.id, error: { code: -32601, message: "method not found" } }
    }
    const out = await reply()
    if (out) process.stdout.write(JSON.stringify(out) + "\n")
  }
})
