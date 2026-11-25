#!/usr/bin/env python3
"""把本地事件队列批量上报到统计服务。

用法：python3 sync-events.py <dash_url> <queue_file>
输出：成功 n 条，失败 m 条
全部成功才删除队列文件（失败保留，下次重试）。
"""
import os
import sys
import urllib.request


def main():
    if len(sys.argv) < 3:
        print("用法: sync-events.py <dash_url> <queue_file>")
        return 2
    dash, queue = sys.argv[1].rstrip("/"), sys.argv[2]
    if not (os.path.exists(queue) and os.path.getsize(queue) > 0):
        print("没有待上报的事件")
        return 0

    ok = fail = 0
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕开 Clash 等系统代理
    with open(queue, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            req = urllib.request.Request(
                dash + "/v1/events", data=line.encode(),
                # 带 UA：Cloudflare 会对默认的 Python-urllib UA 直接 403
                headers={"content-type": "application/json", "user-agent": "doublecheck/0.1"})
            try:
                opener.open(req, timeout=6).read()
                ok += 1
            except Exception as e:  # noqa: BLE001
                fail += 1
                print("  失败原因: %s" % str(e)[:100])
    print("事件上报：成功 %d 条，失败 %d 条" % (ok, fail))
    if fail == 0:
        os.remove(queue)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
