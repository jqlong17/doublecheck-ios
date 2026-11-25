#!/usr/bin/env python3
"""校验 ExportOptions.plist 的 method 是否是当前 Xcode 接受的值。

Xcode 15 起 `app-store` 改成 `app-store-connect`，旧值会直接报错。
"""
import os
import plistlib
import sys

repo = sys.argv[1] if len(sys.argv) > 1 else "."
path = os.path.join(repo, "ExportOptions.plist")
if not os.path.exists(path):
    print("没有 ExportOptions.plist（跳过）")
    sys.exit(0)
with open(path, "rb") as f:
    d = plistlib.load(f)
method = d.get("method")
ok = {"app-store-connect", "app-store", "ad-hoc", "development", "enterprise"}
if method not in ok:
    print("method=%r 不是已知值：%s" % (method, ", ".join(sorted(ok))))
    sys.exit(1)
if method == "app-store":
    print("method=app-store 已废弃，Xcode 15+ 要写 app-store-connect")
    sys.exit(1)
print("ExportOptions.method = %s" % method)
