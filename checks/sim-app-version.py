#!/usr/bin/env python3
"""检查模拟器里已安装的 App 版本是否与仓库 Info.plist 一致。

为什么：改完代码没重装，模拟器里还是旧二进制，表现成「改了没效果」。
"""
import json
import os
import plistlib
import subprocess
import sys

repo = sys.argv[1] if len(sys.argv) > 1 else "."
plist = os.path.join(repo, "Info.plist")
if not os.path.exists(plist):
    print("找不到 Info.plist")
    sys.exit(2)
with open(plist, "rb") as f:
    info = plistlib.load(f)
want = (info.get("CFBundleShortVersionString"), info.get("CFBundleVersion"))

bundle = "com.ruska.dsh-pocket-ios"
try:
    out = subprocess.run(["xcrun", "simctl", "list", "devices", "booted", "-j"],
                         stdout=subprocess.PIPE, check=True).stdout
    devices = json.loads(out).get("devices", {})
    udids = [d["udid"] for ds in devices.values() for d in ds if d.get("state") == "Booted"]
    if not udids:
        print("没有已启动的模拟器，跳过")
        sys.exit(0)
    app = subprocess.run(
        ["xcrun", "simctl", "get_app_container", udids[0], bundle, "app"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if app.returncode != 0:
        print("模拟器里没装 %s，跳过（装一次即可）" % bundle)
        sys.exit(0)
    path = os.path.join(app.stdout.decode().strip(), "Info.plist")
    got_info = plistlib.load(open(path, "rb"))
    got = (got_info.get("CFBundleShortVersionString"), got_info.get("CFBundleVersion"))
except Exception as e:  # noqa: BLE001
    print("无法检查：%s" % str(e)[:80])
    sys.exit(0)

if got != want:
    print("模拟器里的版本是 %s(%s)，仓库是 %s(%s)——改完没重装？" % (got[0], got[1], want[0], want[1]))
    sys.exit(1)
print("模拟器版本与仓库一致：%s(%s)" % (want[0], want[1]))
