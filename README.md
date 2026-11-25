# ops —— 能签字的运维动作

> 每个动作都自带 **前置条件 / 步骤 / 后置断言 / 回滚**。
> 目标不是「更强的 shell」，而是**「agent 可以放心调用的动词」**。

## 为什么

2026-11-25 的真实事故：Mac 上 DSH 进程还在，但 3093 端口没监听，
`tailscale serve` 一直返回 502，手机端完全连不上——**进程活着不等于服务活着**。

这类坑的共同点是：动手前没检查前提，做完没验证结果。
所以每个动作必须回答三个问题：

1. **凭什么现在能做？**（前置条件）
2. **做完怎么算成功？**（后置断言）
3. **失败退到哪？**（回滚）

## 用法

```bash
python3 ops.py list                     # 有哪些动作
python3 ops.py plan service.restart     # 只看：前置条件过不过、会执行什么
python3 ops.py call service.restart     # 演练（不加 --yes 不执行）
python3 ops.py call service.restart --yes
python3 ops.py verify cert.verify       # 只跑后置断言
python3 ops.py lint                     # 校验动作定义（CI 用）
```

`plan` 是这个工具的核心：**它必须先告诉人「现在能不能做、会做什么」，再决定做不做。**

## 动作长什么样

```yaml
schemaVersion: 1
action: service.restart
summary: 重启一个 systemd 服务，并确认端口和 HTTP 真的恢复
incident: |
  2026-11-25：Mac 上 DSH 进程还在，但 3093 端口没监听，
  tailscale serve 一直返回 502，手机端完全连不上。
params:
  unit: dsh-web.service
  port: 3080
preconditions:
  - kind: unit.exists
    unit: "{{unit}}"
  - kind: disk.free_mb_gt
    mb: 200
steps:
  - kind: systemd.restart
    unit: "{{unit}}"
postconditions:
  - kind: port.listening
    port: "{{port}}"
  - kind: http.status
    url: "http://127.0.0.1:{{port}}/"
    expect: [200, 401]
rollback:
  - kind: systemd.start
    unit: "{{unit}}"
```

**`incident` 是必填的**：每个动作都必须能追溯到一次真实事故或明确需求。
写不出 `incident` 的动作，说明还不清楚它防的是什么。

## 现有的断言与步骤

| 断言 | 用途 |
| --- | --- |
| `unit.exists` | systemd unit 是否存在 |
| `systemd.active` | 服务是否 active |
| `port.listening` / `port.free` | 端口状态 |
| `http.status` | 端点返回码是否在预期集合里 |
| `disk.free_mb_gt` | 磁盘余量 |
| `file.exists` | 路径是否存在 |
| `cert.expiry_days` | 证书剩余天数（走真实 TLS 握手） |
| `cmd.exit0` | 任意命令退出码为 0 |

| 步骤 | 用途 |
| --- | --- |
| `systemd.restart` / `systemd.start` | 服务操作（走 busctl，不用 systemctl） |
| `cmd.run` | 执行命令 |
| `fs.prune` | 只清理白名单目录 |
| `noop` | 只读动作占位 |

## CI 闸门

```bash
bash ci/check.sh
```

- 所有动作过 `lint`（必填字段、未知断言、缺后置断言都要报错）
- 只读动作跑一遍 `verify`，必须真的通过
- 变更类动作只跑 `plan`，不执行

## 路线

- [x] v0.1：5 个动作、9 种断言、CI 闸门
- [ ] 负例测试（每个断言要证明自己抓得住违规）
- [ ] registry（按栈分类、可检索）
- [ ] MCP server 封装
- [ ] 服务端判定（规则下发端 + 客户端采集）
