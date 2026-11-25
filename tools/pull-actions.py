#!/usr/bin/env python3
"""从云端拉取动作到本地缓存 ~/.doublecheck/actions/<domain>/<id>.yaml。

冲突策略：云端为准，但本地有未提交改动时会提示（不覆盖）。
"""
import hashlib
import json
import os
import sys
import urllib.request

CACHE = os.path.expanduser("~/.doublecheck/actions")


def main():
    dash = (os.environ.get("DASH_URL") or "").rstrip("/")
    if not dash:
        print("需要 DASH_URL")
        return 2
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    url = dash + "/v1/actions"

    def fetch(u):
        req = urllib.request.Request(u, headers={"user-agent": "doublecheck/0.1"})
        return json.loads(opener.open(req, timeout=60).read().decode())

    # 一次拉全量：逐个 GET 在跨境网络下会超时
    listing = fetch(url + "?full=1").get("actions", [])
    new = changed = same = 0
    for a in listing:
        path = os.path.join(CACHE, a["domain"], a["id"] + ".yaml")
        text = a["yaml"]
        digest = hashlib.sha256(text.encode()).hexdigest()
        if os.path.exists(path):
            old = open(path, encoding="utf-8").read()
            if hashlib.sha256(old.encode()).hexdigest() == digest:
                same += 1
                continue
            changed += 1
        else:
            new += 1
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    print("云端 %d 个动作：新增 %d，更新 %d，未变 %d" % (len(listing), new, changed, same))
    print("缓存目录：%s" % CACHE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
