#!/usr/bin/env python3
"""看最近 24 小时有没有 DSHPocket 的崩溃报告（只读诊断）。"""
import glob
import os
import sys
import time

home = os.path.expanduser("~")
patterns = [os.path.join(home, "Library/Logs/DiagnosticReports/DSHPocket*"),
            os.path.join(home, "Library/Logs/DiagnosticReports/*.ips")]
files = []
for p in patterns:
    files.extend(glob.glob(p))
files = [f for f in set(files) if "DSHPocket" in os.path.basename(f)]

cutoff = time.time() - 24 * 3600
recent = [f for f in files if os.path.getmtime(f) > cutoff]

if not recent:
    print("最近 24 小时没有 DSHPocket 崩溃报告")
    sys.exit(0)

recent.sort(key=os.path.getmtime, reverse=True)
print("最近 24 小时有 %d 份崩溃报告，最新：%s（%s）" % (
    len(recent), os.path.basename(recent[0]),
    time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(recent[0])))))
sys.exit(0)
