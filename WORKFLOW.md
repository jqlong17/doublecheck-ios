# WORKFLOW · 什么时候该跑哪条

> 由 `tools/gen-workflow.py` 从动作元数据生成，不要手改。

## iOS

### 提交前（55 条）　`dc ios check --commit`

| 动作 | 说明 | 类型 |
| --- | --- | --- |
| `git.no-wip-commit` | 最后一次提交不要是 WIP | ◇ |
| `ios.architecture-clean` | 架构分层检查（文件行数、假拆分）必须为 0 违规 | ◇ |
| `ios.docs-not-committed` | docs/ 一律不入库 | ◇ |
| `ios.gitignore-artifacts` | 构建产物（DerivedData/build/xcuserdata）不能进仓库 | ● |
| `ios.l10n-ratchet` | 本地化棘轮——不允许新增未翻译的中文字面量 | ◇ |
| `ios.message-marker` | 客户端标记必须是 U+2063 ×2（iOS 消息来源的唯一判据） | ● |
| `ios.no-hardcoded-fonts` | 禁止 .system(size:) 硬编码字号 | ◇ |
| `ios.no-secrets` | 代码和脚本里不能出现 token、私钥、云密钥 | ● |
| `ios.pbxproj-registered` | 新增的 .swift 文件必须已在 project.pbxproj 注册 | ● |
| `ios.secret-files-ignored` | 签名证书与密钥文件不能被提交 | ● |
| `ios.shell-vars` | shell 脚本里 $VAR 后面不能紧跟中文标点（会被当成变量名的一部分） | ● |
| `ios.tech-index` | TECH_INDEX.md 里每条「文件 · 符号」必须仍然存在 | ◇ |
| `plist.ats-arbitrary` | 不要开启 ATS 的任意加载 | ● |
| `plist.bg-audio` | 用到音频后台播放要声明 background mode | ◇ |
| `plist.build-match` | build 号必须在 Info.plist 与工程设置中一致 | ● |
| `plist.bundle-id-match` | Info.plist 的 bundle id 必须与工程设置一致 | ● |
| `plist.camera-usage` | 用到相机就必须有相机用途说明 | ● |
| `plist.launch-screen` | iOS 14+ 需要 UILaunchScreen | ● |
| `plist.mic-usage` | 用到麦克风就必须有麦克风用途说明 | ● |
| `plist.orientation` | 必须声明支持的屏幕方向 | ◇ |
| `plist.photos-usage` | 用到相册就必须有相册用途说明 | ● |
| `plist.version-match` | 版本号必须在 Info.plist 与工程设置中一致 | ● |
| `repo.ci-workflow` | 仓库要有 CI 配置 | ◇ |
| `repo.ds-store` | .DS_Store 不能进仓库 | ● |
| `repo.editorconfig` | 建议有 .editorconfig | ◇ |
| `repo.gitattributes` | 建议有 .gitattributes 处理二进制与换行 | ◇ |
| `repo.gitignore-xcuserdata` | .gitignore 必须包含 xcuserdata | ● |
| `repo.large-file` | 不要提交大于 2MB 的文件 | ● |
| `repo.license` | 仓库要有 LICENSE | ◇ |
| `repo.readme` | 仓库要有 README | ◇ |
| `repo.spm-resolved` | Package.resolved 要提交 | ● |
| `repo.swiftlint-config` | 建议有 SwiftLint / SwiftFormat 配置 | ◇ |
| `swift.anyview` | 避免 AnyView（拖慢 SwiftUI diff） | ◇ |
| `swift.async-after` | 慎用 asyncAfter 做时序控制 | ◇ |
| `swift.bundle-id-literal` | 代码里不要写死 bundle id | ◇ |
| `swift.dispatch-main-sync` | 不要在主线程序列上同步等待 | ◇ |
| `swift.fatal-error` | 生产代码里不要 fatalError | ◇ |
| `swift.force-cast` | 禁止 as!（类型不符直接崩） | ◇ |
| `swift.force-first-last` | 谨慎使用 .first! / .last! | ◇ |
| `swift.foreground-color` | 用 foregroundStyle 替代已废弃的 foregroundColor | ◇ |
| `swift.hardcoded-color` | 禁止 Color(red:green:blue:) 硬编码颜色 | ◇ |
| `swift.hardcoded-frame` | 避免写死 frame 尺寸 | ◇ |
| `swift.http-url` | 代码里不允许出现 http:// 明文地址 | ◇ |
| `swift.localhost-url` | 代码里不要写死 127.0.0.1 / localhost | ◇ |
| `swift.magic-timeout` | 网络超时不要写魔法数字 | ◇ |
| `swift.notification-string` | 通知名不要用裸字符串 | ◇ |
| `swift.nslog` | 用 Logger 替代 NSLog | ◇ |
| `swift.print` | 生产代码里不要用 print 打日志 | ◇ |
| `swift.string-format-multi` | String(format:) 多参数要小心顺序 | ◇ |
| `swift.thread-sleep` | 禁止在主线程 sleep | ◇ |
| `swift.todo-no-ref` | TODO/FIXME 必须带 issue 引用 | ◇ |
| `swift.try-bang` | 禁止 try!（崩了就是线上崩溃） | ◇ |
| `swift.uiwebview` | 禁止使用已废弃的 UIWebView | ● |
| `swift.userdefaults-key` | UserDefaults 的 key 不要用裸字符串 | ◇ |
| `swift.weak-self` | 逃逸闭包引用 self 时要显式声明捕获列表 | ◇ |

### 构建（2 条）　`dc ios check --build`

| 动作 | 说明 | 类型 |
| --- | --- | --- |
| `ios.clean-build` | 全新构建（清 derivedData），用于验证改了 DSHKit 之后的行为 | ● |
| `ios.sim-build` | 在模拟器上编译 App（不签名），确认改动能通过编译 | ● |

### 测试（1 条）　`dc ios check --test`

| 动作 | 说明 | 类型 |
| --- | --- | --- |
| `ios.ui-tests-gate` | 发版前必须真跑 UI 测试，跳过的用例单独报出来 | ◇ |

### 发版（11 条）　`dc ios check --release`

| 动作 | 说明 | 类型 |
| --- | --- | --- |
| `assets.appicon-1024` | AppIcon 必须包含 1024 尺寸 | ● |
| `assets.privacy-manifest` | 要有 PrivacyInfo.xcprivacy | ● |
| `git.branch-main` | 发版应该从主分支出 | ◇ |
| `git.clean-tree` | 发版前工作区必须干净 | ◇ |
| `git.tag-matches-version` | git tag 必须与版本号一致 | ◇ |
| `ios.build-number-unique` | 上传前确认 build 号没被用过（重复会判 INVALID_BINARY） | ● |
| `ios.export-options-valid` | ExportOptions.plist 的 method 必须是当前 Xcode 接受的值 | ● |
| `ios.proxy-off-before-upload` | 上传 App Store 前必须确认系统代理已关闭 | ◇ |
| `plist.export-compliance` | 必须声明出口合规（否则每次上传都被问） | ● |
| `repo.changelog` | 要有 CHANGELOG | ◇ |
| `repo.screenshots-dir` | 商店截图要有固定目录 | ◇ |

### 运行时（3 条）

| 动作 | 说明 | 类型 |
| --- | --- | --- |
| `ios.crash-reports` | 看最近 24 小时有没有 DSHPocket 的崩溃报告（只读） | ○ |
| `ios.message-origin` | 判断最近一条用户消息是手机发的还是电脑发的（只读） | ○ |
| `ios.sim-app-version` | 模拟器里已安装的 App 版本必须与仓库 Info.plist 一致 | ● |

## Linux / systemd

### 运行时（15 条）

| 动作 | 说明 | 类型 |
| --- | --- | --- |
| `disk.cleanup` | 清理已知的构建缓存目录，并在之后确认磁盘水位 | ● |
| `env.preflight` | 跑一遍带检验的记忆库，确认当前环境的前提仍然成立（只读） | ● |
| `linux.core-dump` | 生产机应关闭 core dump | ◇ |
| `linux.disk-inode` | inode 使用率不能超过 80% | ● |
| `linux.dns-resolv` | DNS 解析必须正常 | ● |
| `linux.firewall-active` | 防火墙必须处于启用状态 | ● |
| `linux.journald-limit` | journald 必须配置容量上限 | ● |
| `linux.logrotate` | 日志必须配置轮转 | ● |
| `linux.memory-available` | 可用内存不能低于 200MB | ● |
| `linux.ssh-root-login` | 禁止 root 直接 SSH 登录 | ● |
| `linux.sudo-nopasswd` | 禁止无密码 sudo ALL | ● |
| `linux.swap-pressure` | swap 使用率不能超过 50% | ◇ |
| `linux.time-sync` | 系统时间必须同步 | ● |
| `port.privileged-bind` | 绑定小于 1024 的端口时，systemd unit 必须保留 CAP_NET_BIND_SERVICE | ● |
| `service.restart` | 重启一个 systemd 服务，并确认端口和 HTTP 真的恢复 | ● |

## 网络 / TLS

### 运行时（13 条）

| 动作 | 说明 | 类型 |
| --- | --- | --- |
| `cert.verify` | 检查某个域名的 TLS 证书还剩多少天（只读） | ● |
| `http.health` | 检查一个 HTTP 端点是否返回预期状态码（只读） | ● |
| `net.cert-chain` | 证书链必须完整 | ● |
| `net.csp` | 建议配置 Content-Security-Policy | ◇ |
| `net.dns-resolves` | 域名必须能解析 | ● |
| `net.gzip` | 文本响应要开启压缩 | ◇ |
| `net.hsts` | HTTPS 响应要带 HSTS | ◇ |
| `net.http-to-https` | HTTP 必须跳转到 HTTPS | ● |
| `net.server-header` | 隐藏服务器版本信息 | ◇ |
| `net.tls-version` | TLS 至少 1.2 | ● |
| `net.xcto` | 响应要带 X-Content-Type-Options | ◇ |
| `port.owner` | 查某个端口被谁占用、绑在哪个地址（只读诊断） | ○ |
| `tls.sni-match` | 检查某个域名拿到的证书是否真的匹配它（只读） | ● |

## 图例

| 标记 | 类型 | 失败时 |
| --- | --- | --- |
| ● | 不变式 | 阻断 |
| ◇ | 策略 | 提示 |
| ○ | 诊断 | 不阻断 |
