#!/usr/bin/env node
// 拉取云端动作并验签。公钥固定在本仓库 keys/registry.pub（首次拉取时也写进 D1，二者必须一致）
import { createHash, createPublicKey, verify } from "node:crypto"
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import { homedir } from "node:os"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..")
const dash = (process.env.DASH_URL || "").replace(/\/$/, "")
if (!dash) {
  console.error("需要 DASH_URL")
  process.exit(2)
}
const pub = createPublicKey(readFileSync(join(ROOT, "keys", "registry.pub"), "utf8"))
const CACHE = join(homedir(), ".doublecheck", "actions")

const res = await fetch(dash + "/v1/actions?full=1", { headers: { "user-agent": "doublecheck/0.1" } })
if (!res.ok) {
  console.error("拉取失败 HTTP", res.status)
  process.exit(1)
}
let { actions = [] } = await res.json()

// --stack commit|build|release|ops|all：只装这一组
const stackArg = process.argv.indexOf("--stack")
if (stackArg > -1) {
  const name = process.argv[stackArg + 1]
  const STAGES = {
    commit: ["commit"],
    build: ["build", "test"],
    release: ["build", "test", "release"],
    ops: ["operate"],
  }
  if (name !== "all") {
    const want = STAGES[name]
    if (!want) {
      console.error("未知 stack：%s（可选 commit / build / release / ops / all）", name)
      process.exit(2)
    }
    actions = actions.filter((a) => want.includes(a.stage))
  }
  console.log("stack=%s → %d 个动作", name, actions.length)
}

let added = 0, updated = 0, same = 0, bad = 0
for (const a of actions) {
  const data = Buffer.from(a.yaml)
  // 先校验内容哈希，再验签：任何一层不对都拒绝写入
  if (createHash("sha256").update(data).digest("hex") !== a.sha256) { bad++; console.error("sha256 不匹配:", a.id); continue }
  if (!a.signature || !verify(null, data, pub, Buffer.from(a.signature, "base64"))) {
    bad++; console.error("签名无效:", a.id); continue
  }
  const path = join(CACHE, a.platform, a.id + ".yaml")
  if (existsSync(path)) {
    same += readFileSync(path, "utf8") === a.yaml ? 1 : (writeFileSync(path, a.yaml), updated++, 0)
  } else {
    mkdirSync(dirname(path), { recursive: true })
    writeFileSync(path, a.yaml)
    added++
  }
}
console.log(`云端 ${actions.length} 个动作：新增 ${added}，更新 ${updated}，未变 ${same}，验签失败 ${bad}`)
if (bad) process.exit(1)
