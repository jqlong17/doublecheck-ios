#!/usr/bin/env python3
"""动作分组（stack）：一次装一组，而不是一次装 100 个。"""

STACKS = {
    "commit":  {"title": "提交前", "when": "每次 git commit 前", "match": lambda a: a.get("stage") == "commit"},
    "build":   {"title": "构建",   "when": "改完代码要验证能编过", "match": lambda a: a.get("stage") in ("build", "test")},
    "release": {"title": "发版",   "when": "上传 App Store / TestFlight 前", "match": lambda a: a.get("stage") in ("build", "test", "release")},
    "ops":     {"title": "运行时", "when": "服务器与网络日常体检", "match": lambda a: a.get("platform") in ("linux", "net") or a.get("stage") == "operate"},
    "all":     {"title": "全部",   "when": "新机器一次装齐", "match": lambda a: True},
}


def pick(actions, name):
    stack = STACKS.get(name)
    if not stack:
        return None
    return [a for a in actions if stack["match"](a) and a.get("kind") != "diagnostic"]
