#!/usr/bin/env node
// 生成注册表签名密钥（Ed25519）。私钥只留在本机 ~/.doublecheck/registry.key
import { generateKeyPairSync } from "node:crypto"
import { writeFileSync, existsSync, mkdirSync } from "node:fs"
import { homedir } from "node:os"
import { join } from "node:path"

const home = join(homedir(), ".doublecheck")
mkdirSync(home, { recursive: true })
const priv = join(home, "registry.key")

if (existsSync(priv) && !process.argv.includes("--force")) {
  console.error("密钥已存在：" + priv + "（加 --force 覆盖）")
  process.exit(1)
}
const { publicKey, privateKey } = generateKeyPairSync("ed25519")
const pubPem = publicKey.export({ type: "spki", format: "pem" })
writeFileSync(priv, privateKey.export({ type: "pkcs8", format: "pem" }), { mode: 0o600 })
console.log("私钥：" + priv)
console.log("公钥（放进 keys/registry.pub 并填进 D1 meta）：")
console.log(pubPem)
