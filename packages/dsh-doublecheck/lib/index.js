/**
 * dsh-doublecheck —— 把 doublecheck 的动作暴露成 DSH 工具。
 *
 * 设计原则：插件本身不实现检查逻辑，只负责「把 dc 命令变成工具调用」。
 * 这样规则、动作、证据都在 doublecheck 里，插件可以极薄。
 *
 * 依赖：机器上装有 doublecheck（`dc` 在 PATH，或设置 DC_BIN）。
 */
import { execFile } from "node:child_process"

export const name = "dsh-doublecheck"
export const inject = ["tools"]

const DC = process.env.DC_BIN || "dc"

const TEXT_OUTPUT = {
  schema: { type: "string" },
  render: (_args, value) => [{ type: "text", text: String(value) }],
}

function run(args, timeoutMs = 120000) {
  return new Promise((resolve) => {
    execFile(DC, args, { timeout: timeoutMs, maxBuffer: 4 * 1024 * 1024 }, (err, stdout, stderr) => {
      const text = [stdout, stderr].filter(Boolean).join("\n").trim()
      resolve({ ok: !err, text: text || (err ? String(err) : "") })
    })
  })
}

function kv(params = {}) {
  return Object.entries(params).map(([k, v]) => `${k}=${v}`)
}

function toolDefs() {
  return [
    {
      name: "dc_list",
      description: "列出本机可用的标准动作（已按 ios/linux/net 领域分组）。",
      parameters: {},
      output: TEXT_OUTPUT,
      async execute() {
        const r = await run(["list"])
        return r.text
      },
    },
    {
      name: "dc_plan",
      description:
        "预检：评估某个标准动作的前置条件，返回它会做什么、失败怎么回滚。不执行任何步骤。",
      parameters: {
        action: { type: "string", description: "动作 id，例如 ios.pbxproj-registered" },
        params: { type: "object", description: "参数覆盖，例如 {\"repo\":\"/path/to/repo\"}" },
      },
      output: TEXT_OUTPUT,
      async execute(args) {
        const r = await run(["plan", args.action, "--json", ...kv(args.params)])
        return r.text
      },
    },
    {
      name: "dc_verify",
      description: "复检：只跑某个动作的后置断言，确认结果仍然成立。",
      parameters: {
        action: { type: "string" },
        params: { type: "object" },
      },
      output: TEXT_OUTPUT,
      async execute(args) {
        const r = await run(["verify", args.action, "--json", ...kv(args.params)])
        return r.text
      },
    },
    {
      name: "dc_call",
      description:
        "执行一个标准动作。默认演练；只有用户明确确认后才传 confirm=true 真正执行。",
      parameters: {
        action: { type: "string" },
        params: { type: "object" },
        confirm: { type: "boolean", description: "true 表示真的执行步骤" },
      },
      output: TEXT_OUTPUT,
      async execute(args) {
        const extra = args.confirm ? ["--yes"] : []
        const r = await run(["call", args.action, ...kv(args.params), ...extra], 600000)
        return r.text
      },
    },
  ]
}

export async function apply(ctx) {
  const register = ctx?.tools?.register
  if (typeof register !== "function") return
  let defineTool = null
  try {
    const mod = await import("@deepseek-ai/dsh-tools")
    if (typeof mod?.defineTool === "function") defineTool = mod.defineTool
  } catch {
    /* 宿主没提供就退回普通对象 */
  }
  for (const def of toolDefs()) {
    try {
      register.call(ctx.tools, defineTool ? defineTool(def) : def)
    } catch {
      /* 单个工具失败不影响其它 */
    }
  }
}
