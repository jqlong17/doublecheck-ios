#!/usr/bin/env python3
"""从 rulebook 生成动作 YAML（已存在的同名文件不覆盖）。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "checks"))
import rulebook  # noqa: E402

PLATFORM = {"swift": "ios", "plist": "ios", "assets": "ios", "repo": "ios",
            "git": "ios", "linux": "linux", "net": "net"}


def yaml_quote(text, indent):
    lines = text.strip().splitlines()
    pad = " " * indent
    return "\n".join(pad + l for l in lines)


def main():
    made = 0
    for r in rulebook.RULES:
        platform = PLATFORM[r["id"].split(".")[0]]
        path = os.path.join(ROOT, "actions", platform, r["id"] + ".yaml")
        if os.path.exists(path) and "--force" not in sys.argv:
            continue
        needs_host = "{{host}}" in str(r["check"])
        params = ["params:", "  repo: ."]
        if needs_host:
            params.append("  host: ruska.cn")
        run = "python3 {{ops_dir}}/checks/rules.py %s {{repo}}" % r["id"]
        if needs_host:
            run += " host={{host}}"
        doc = "\n".join([
            "schemaVersion: 1",
            "kind: %s" % r["kind"],
            "stage: %s" % r["stage"],
            "area: %s" % r["area"],
            "domain: %s" % r["domain"],
            "action: %s" % r["id"],
            "summary: %s" % r["summary"],
            "incident: |",
            yaml_quote(r["incident"], 2),
            "requires: %s" % ("[%s]" % ", ".join(r["requires"]) if r["requires"] else "[]"),
            *params,
            "preconditions: []",
            "steps:",
            "  - kind: noop",
            "postconditions:",
            "  - kind: cmd.exit0",
            "    timeout_s: 60",
            "    run: %s" % run,
            "",
        ])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc)
        made += 1
    print("生成 %d 个动作" % made)
    total = sum(len([f for f in os.listdir(os.path.join(ROOT, "actions", p)) if f.endswith(".yaml")])
                for p in os.listdir(os.path.join(ROOT, "actions")))
    print("动作总数：%d" % total)


if __name__ == "__main__":
    main()
