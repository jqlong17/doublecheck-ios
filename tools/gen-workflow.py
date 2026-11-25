#!/usr/bin/env python3
"""从动作元数据生成 WORKFLOW.md：什么时候该跑哪条。"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLATFORM = {"ios": "iOS", "linux": "Linux / systemd", "net": "网络 / TLS"}
STAGE = {"commit": "提交前", "build": "构建", "test": "测试", "release": "发版", "operate": "运行时"}
KIND = {"invariant": "●", "policy": "◇", "diagnostic": "○"}
COMMAND = {
    ("ios", "commit"): "dc ios check --commit",
    ("ios", "build"): "dc ios check --build",
    ("ios", "test"): "dc ios check --test",
    ("ios", "release"): "dc ios check --release",
}


def load():
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "actions", "*", "*.yaml"))):
        text = open(path, encoding="utf-8").read()
        g = lambda k: (re.search(r"^%s:\s*(\S+)" % k, text, re.M) or [None, ""])[1]
        s = lambda k: (re.search(r"^%s:\s*(.+)$" % k, text, re.M) or [None, ""])[1].strip()
        out.append(dict(id=g("action"), platform=os.path.basename(os.path.dirname(path)),
                        stage=g("stage"), domain=g("domain"), kind=g("kind"),
                        summary=s("summary")))
    return out


def main():
    actions = load()
    lines = ["# WORKFLOW · 什么时候该跑哪条", "",
             "> 由 `tools/gen-workflow.py` 从动作元数据生成，不要手改。", ""]

    for platform in ("ios", "linux", "net"):
        items = [a for a in actions if a["platform"] == platform]
        if not items:
            continue
        lines.append("## %s" % PLATFORM[platform])
        lines.append("")
        for stage in ("commit", "build", "test", "release", "operate"):
            group = [a for a in items if a["stage"] == stage]
            if not group:
                continue
            cmd = COMMAND.get((platform, stage))
            lines.append("### %s（%d 条）%s" % (STAGE[stage], len(group),
                                               "　`%s`" % cmd if cmd else ""))
            lines.append("")
            lines.append("| 动作 | 说明 | 类型 |")
            lines.append("| --- | --- | --- |")
            for a in group:
                lines.append("| `%s` | %s | %s |" % (a["id"], a["summary"], KIND.get(a["kind"], "")))
            lines.append("")

    lines += ["## 图例", "",
              "| 标记 | 类型 | 失败时 |", "| --- | --- | --- |",
              "| ● | 不变式 | 阻断 |", "| ◇ | 策略 | 提示 |", "| ○ | 诊断 | 不阻断 |", ""]
    path = os.path.join(ROOT, "WORKFLOW.md")
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    print("已生成 WORKFLOW.md（%d 条动作）" % len(actions))


if __name__ == "__main__":
    sys.exit(main())
