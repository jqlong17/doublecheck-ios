#!/usr/bin/env python3
"""判断最近一条用户消息是手机发的还是电脑发的（只读诊断）。

iOS 发出的消息末尾带 U+2063 ×2，Mac 桌面端不带。
分不清来源时，会在错误的一侧白查很久（2026-11-18 就发生过）。
"""
import glob
import json
import os
import subprocess
import sys


def main():
    home = os.path.expanduser("~")
    pattern = os.path.join(home, ".dsh/sessions/*dsh-pocket-ios*/session-*/session.v4.jsonl.zstd")
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if not files:
        print("没找到 iOS App 的会话日志（%s）" % pattern)
        return 2

    raw = subprocess.run(["zstd", "-dc", files[0]], stdout=subprocess.PIPE).stdout.decode("utf-8", "replace")
    last = None
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        # 必须同时限定 source.kind == 'user'：type 为 user/message 的还有系统注入
        if o.get("type") == "user/message" and (o.get("data") or {}).get("source", {}).get("kind") == "user":
            last = o
    if not last:
        print("日志里没有用户消息：%s" % files[0])
        return 1

    text = ""
    for b in last["data"].get("content", []):
        if b.get("type") == "text":
            text = b["text"]
    origin = "iOS（手机）" if text.endswith("\u2063\u2063") else "Mac（桌面端）"
    print("最近一条用户消息来自 %s | 末尾：%r | 会话：%s" % (origin, text[-8:], os.path.basename(files[0])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
