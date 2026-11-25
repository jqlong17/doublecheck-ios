#!/usr/bin/env python3
"""把本地动作推到云端（需要 DC_PUSH_TOKEN）。"""
import glob
import hashlib
import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    dash = (os.environ.get("DASH_URL") or "").rstrip("/")
    token = os.environ.get("DC_PUSH_TOKEN") or ""
    if not dash or not token:
        print("需要 DASH_URL 和 DC_PUSH_TOKEN")
        return 2

    items = []
    for path in sorted(glob.glob(os.path.join(ROOT, "actions", "*", "*.yaml"))):
        yaml_text = open(path, encoding="utf-8").read()
        domain = os.path.basename(os.path.dirname(path))
        action_id = os.path.basename(path)[:-5]
        items.append({
            "id": action_id,
            "domain": domain,
            "version": "0.1.0",
            "yaml": yaml_text,
            "sha256": hashlib.sha256(yaml_text.encode()).hexdigest(),
        })

    req = urllib.request.Request(
        dash + "/v1/actions", data=json.dumps(items).encode(),
        headers={"content-type": "application/json", "authorization": "Bearer " + token,
                 "user-agent": "doublecheck/0.1"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        body = opener.open(req, timeout=60).read().decode()
    except Exception as e:  # noqa: BLE001
        print("推送失败:", e)
        return 1
    print("已推送：", body)
    return 0


if __name__ == "__main__":
    sys.exit(main())
