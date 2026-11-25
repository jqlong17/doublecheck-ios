# doublecheck · iOS

> 写 iOS 时，AI 最容易踩的坑，一条命令全查。

这个包把 **iOS 开发中反复踩到的坑**做成可执行检查。每一条都对应一次真实事故，
不是“一般认为应该这样”。

## 装

```bash
npm i -g doublecheck-ios      # 装到全局，得到 dc 命令
dc ios check --fast --repo .  # 在你的 iOS 仓库根目录跑
```

不想装全局也可以 `npx doublecheck-ios dc ios check --fast`，或者直接把仓库克隆到 `~/ops`（需要 python3 + PyYAML）。

依赖：`python3`（3.6+）、`PyYAML`、macOS 的 `git`。
`--fast` 不需要 Xcode；`--build` / `--release` 才需要。

## 三种时机

| 阶段 | 命令 | 耗时 | 内容 |
| --- | --- | --- | --- |
| 提交前 | `dc ios check --commit`（别名 `--fast`） | < 3 秒 | 只读：pbxproj、字号、密钥、shell 变量、l10n、索引 |
| 构建 | `dc ios check --build` | 1–3 分钟 | 真编译：模拟器构建、全新构建 |
| 测试 | `dc ios check --test` | 3–5 分钟 | UI 测试门禁（跳过的用例算没测） |
| 发版 | `dc ios check --release` | 5–10 分钟 | 全部阶段 + build 号查重 + 代理检查 |

每个动作在 manifest 里都有 `stage` 字段，`dc ios check` 按阶段挑选；
只读动作走 `verify`，有实际步骤的动作走 `call --yes`（不执行等于没检查）。

## 接进工作流

**① git 钩子（推荐）**

```bash
cp ~/ops/templates/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

之后每次 `git commit` 都会先跑一遍 `--fast`。检查不过就提交不了。
临时跳过：`git commit --no-verify`。

**② Xcode Run Script**

把 `templates/xcode-run-script.sh` 的内容贴到 Build Phases → Run Script。
构建时自动检查，红了直接编译失败。

**③ CI**

```yaml
- run: ~/ops/dc ios check --release --repo .
```

## 现在有哪些检查

| 检查 | 防的是什么 |
| --- | --- |
| `ios.pbxproj-registered` | 新增 `.swift` 没注册进工程文件，别人拉下来编译失败 |
| `ios.docs-not-committed` | `docs/` 被顺手提交（内部资料外泄 / 仓库膨胀） |
| `ios.no-hardcoded-fonts` | `.system(size:)` 硬编码字号，动态字体下不一致 |
| `ios.architecture-clean` | 文件行数超阈值、拆了但职责没分开 |
| `ios.sim-build` | 只跑单测没验证能否编译 |
| `ios.clean-build` | 改了本地 Package 却用增量构建，链接旧产物 |

每条检查的 YAML 里都有 `incident` 字段，写清它来自哪次事故。

## 失败了怎么办

1. **先看是哪条、什么原因**——输出里会写明文件行号
2. **判断是真问题还是误报**——误报请提 issue，附上最小的复现仓库
3. **临时放行**：`git commit --no-verify`（不推荐长期用）

## 设计原则

- **宁可少，不可吵**：只上有 fixture 的检查，误报率 > 5% 的一律不上
- **不自动改代码**：只检查，不 fix。修不修、怎么修由你决定
- **每条可追溯**：没有事故来源的检查不许进库

## 退出码

| 码 | 含义 |
| --- | --- |
| 0 | 全部通过 |
| 1 | 有检查失败 |
| 2 | 用法错误 / 环境问题 |

## 动作分发（签名）

```bash
dc pull     # 从云端拉动作，逐个校验 sha256 + Ed25519 签名
dc push     # 把本地动作签名后推到云端（需要 DC_PUSH_TOKEN）
```

- 私钥只在作者机器上：`~/.doublecheck/registry.key`（0600）
- 公钥固定在仓库里：`keys/registry.pub`，拉取时用它验签
- **验签失败的动作不会写入本地缓存**，`dc pull` 会列出被拒绝的 id

这条是必须的：没有签名，中间人改一个 YAML 就等于让你的机器执行任意命令。

## 四个维度

| 维度 | 取值 | 回答什么 | 看板上的位置 |
| --- | --- | --- | --- |
| **platform 平台** | ios / linux / net | 跑在哪 | 一级标题 |
| **domain 领域** | 代码质量 / 交付发布 / 运行时 / 工程配置 | 防的是哪类问题 | 二级标题 |
| **area 模块** | 工程 / 连接 / 消息 / 对话 / 设置 / 插件 / 系统 | 影响哪个功能 | 行内标签 |
| **stage 阶段** | 提交前 / 构建 / 测试 / 发版 / 运行时 | 什么时候跑 | 行内标签 |
| **kind 类型** | 不变式 / 策略 / 诊断 | 失败了算不算数 | 行内标签 |

分组看的是前两个：**平台决定你在哪台机器上跑，领域决定这一组检查在防哪类问题。**

## 三类动作：不是所有检查都有“对错”

| 标记 | 类型 | 含义 | 失败时 |
| --- | --- | --- | --- |
| ● | `invariant` 不变式 | 客观上就是错的（编译不过、Apple 拒收、shell 报错） | **阻断**，退出码 1 |
| ◇ | `policy` 策略 | 项目的偏好（docs 要不要入库、字号规范、索引要不要维护） | **只提示**，`--strict` 才阻断 |
| ○ | `diagnostic` 诊断 | 只输出信息，不判定 | 不阻断 |

`docs/` 是否入库是**你的选择**，不是普世规则。所以它被归为策略，且默认不检查——
要在某个仓库启用，就在仓库根写：

```yaml
# .doublecheck.yaml
version: 1
policies:
  docs.tracked: forbid     # forbid = 禁止入库；allow = 允许
```

没写这个文件 → 检查直接跳过，只打印一句「未配置策略」。

**设计原则：不变式替你把关，策略让你自己定。** 一个工具如果把自己的口味当真理，
用户第一周就会卸载它。
