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

| 时机 | 命令 | 耗时 | 用途 |
| --- | --- | --- | --- |
| 提交前 | `dc ios check --fast` | < 3 秒 | 只读检查，不碰构建 |
| 构建后 | `dc ios check --build` | 1–3 分钟 | 含模拟器编译 |
| 发版前 | `dc ios check --release` | 3–10 分钟 | 含全新构建 |

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
