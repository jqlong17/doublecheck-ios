#!/usr/bin/env python3
"""打印配置里的 dashUrl（没有就输出空）。"""
import json
import os
import sys

path = os.path.expanduser("~/.doublecheck/config.json")
try:
    print(json.load(open(path)).get("dashUrl") or "")
except Exception:  # noqa: BLE001
    print("")
