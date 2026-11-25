#!/usr/bin/env node
// 把本地动作签名后推到云端。私钥：~/.doublecheck/registry.key
import { createHash, createPrivateKey, sign } from "node:crypto"
import { globSync, readFileSync } from "node:fs"
import { homedir } from "node:os"
import { join, basename, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..")
const dash = (process.env.DASH_URL || "").replace(/\/$/, "")
const token = process.env.DC_PUSH_TOKEN || ""
if (!dash || !token) {
  console.error("需要 DASH_URL 和 DC_PUSH_TOKEN")
  process.exit(2)
}
const keyPath = join(homedir(), ".doublecheck", "registry.key")
const priv = createPrivateKey(readFileSync(keyPath, "utf8"))

const files = globSync(join(ROOT, "actions", "*", "*.yaml"))
const items = files.map((path) => {
  const yaml = readFileSync(path, "utf8")
  const domain = basename(dirname(path))
  const id = basename(path, ".yaml")
  const m = yaml.match(/^summary:\s*(.+)$/m)
  const summary = m ? m[1].trim() : ""
  const km = yaml.match(/^kind:\s*(\S+)/m)
  const kind = km ? km[1] : "invariant"
  const sm = yaml.match(/^stage:\s*(\S+)/m)
  const stage = sm ? sm[1] : "operate"
  return {
    summary,
    kind,
    stage,
    id,
    domain,
    version: "0.1.0",
    yaml,
    sha256: createHash("sha256").update(yaml).digest("hex"),
    signature: sign(null, Buffer.from(yaml), priv).toString("base64"),
  }
})

const res = await fetch(dash + "/v1/actions", {
  method: "POST",
  headers: {
    "content-type": "application/json",
    authorization: "Bearer " + token,
    "user-agent": "doublecheck/0.1",
  },
  body: JSON.stringify(items),
})
console.log("HTTP", res.status, await res.text())
