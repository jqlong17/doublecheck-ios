#!/usr/bin/env python3
"""把一次动作调用写进本地队列（不联网）。

为什么不在调用时直接上报：国内到 Cloudflare 的 TLS 握手就要 1 秒上下，
放在用户的关键路径上会让每条 `dc verify` 都变慢。改成先写队列，
由 `dc sync` 批量上报（可挂 launchd 定时）。
"""
import json
import os
import sys
import time

def main():
    if len(sys.argv) < 5:
        return 1
    tool, action, rc, _dash, agent = sys.argv[1:6]
    home = os.path.expanduser("~/.doublecheck")
    os.makedirs(home, exist_ok=True)
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": tool,
        "action": action,
        "ok": rc == "0",
        "agent": agent,
    }
    with open(os.path.join(home, "events-queue.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main())
