# dsh-doublecheck

把 [doublecheck](../..) 的标准动作暴露成 DSH 工具：

| 工具 | 作用 |
| --- | --- |
| `dc_list` | 列出动作（按 ios/linux/net 分组） |
| `dc_plan` | 预检：能不能做、会做什么、失败怎么退 |
| `dc_verify` | 复检：只跑后置断言 |
| `dc_call` | 执行（默认演练，`confirm=true` 才真跑） |

## 安装

```bash
npm i -g doublecheck          # 提供 dc 命令
npm i -g dsh-doublecheck      # 插件
```

插件本身不含规则，所有检查逻辑在 `doublecheck` 里；`dc` 不在 PATH 时可用 `DC_BIN` 指定。

## 在 DSH 里用

装好后工具自动出现。典型对话：

> 用户：改完 DSHKit 了，帮我验证一下会不会链接旧产物
> 助手：（dc_plan ios.clean-build）→（dc_call，confirm 后）→（dc_verify）

**约定**：先 plan、再 call、call 完必须 verify。
