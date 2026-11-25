#!/usr/bin/env python3
"""校验客户端来源标记：PromptPayload.clientMark 必须是 U+2063 ×2。

为什么是硬性契约：iOS 发出的消息靠这两个不可见字符和 Mac 区分开
（DSH 的 source 只有 kind/rpcId/clientTimeZone，没有客户端标识）。
标记一改，来源判据就失效，排查「手机发的还是电脑发的」会全线出错。
"""
import os
import re
import sys

repo = sys.argv[1] if len(sys.argv) > 1 else "."
path = os.path.join(repo, "DSHKit/Sources/DSHKit/Protocol/PromptPayload.swift")
if not os.path.exists(path):
    print("找不到 PromptPayload.swift（--repo 指向 iOS 仓库根目录了吗？）")
    sys.exit(2)

src = open(path, encoding="utf-8").read()
m = re.search(r'clientMark\s*=\s*"([^"]*)"', src)
if not m:
    print("PromptPayload.swift 里找不到 clientMark 定义")
    sys.exit(1)

# Swift 源码里是 \u{2063} 形式，不能直接 unicode_escape（\u{ 不是合法转义）
value = re.sub(r"\\u\{([0-9A-Fa-f]+)\}", lambda mm: chr(int(mm.group(1), 16)), m.group(1))
if value != "\u2063\u2063":
    print("clientMark 被改动：期望 U+2063 ×2，实际 %r（%d 个字符）" % (value, len(value)))
    sys.exit(1)
print("clientMark 正确（U+2063 ×2）")
