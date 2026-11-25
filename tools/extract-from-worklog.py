#!/usr/bin/env python3
"""从 worklog 的 incident / fix 条目里提“候选动作”，写到 doublecheck 的 inbox。

不自动生成动作——只把原料摊开：
  这次事故 → 该防的是什么 → 前置条件写什么 → 后置断言怎么验
"""
import glob
import json
import os
import sys
from datetime import datetime

WORKLOG = os.environ.get("WORKLOG", "/root/worklog")
DC_HOME = os.path.expanduser(os.environ.get("DC_HOME", "~/.doublecheck"))
STATE = os.path.join(DC_HOME, "worklog-extract-state.json")
INBOX = os.path.join(DC_HOME, "inbox")
INTERESTING = {"incident", "fix", "fact_correction"}


def main():
    state = {"last_at": "1970-01-01T00:00:00"}
    if os.path.exists(STATE):
        try:
            state = json.load(open(STATE, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    last = state.get("last_at", "")

    rows = []
    for path in sorted(glob.glob(os.path.join(WORKLOG, "2026-*", "journal.jsonl"))):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if d.get("at", "") <= last:
                continue
            if d.get("kind") in INTERESTING:
                rows.append(d)

    if not rows:
        print("没有新的 incident/fix 条目（上次处理到 %s）" % (last or "从未"))
        return 0

    os.makedirs(INBOX, exist_ok=True)
    out = os.path.join(INBOX, "from-worklog-%s.md" % datetime.now().strftime("%Y%m%d-%H%M"))
    with open(out, "w", encoding="utf-8") as f:
        f.write("# 从 worklog 提炼的候选动作（%d 条）\n\n" % len(rows))
        f.write("每条问三件事：**它防的是什么？** **前置条件是什么？** **做完怎么验？**\n\n")
        for d in rows:
            f.write("## %s `%s`\n" % (d.get("at", "")[:16], d.get("kind")))
            f.write("- 摘要：%s\n" % d.get("summary", ""))
            detail = (d.get("detail") or "").replace("\n", " ")
            if detail:
                f.write("- 细节：%s\n" % detail[:280])
            f.write("- 作者：%s\n" % (d.get("author", {}).get("id") or d.get("host", "?")))
            f.write("- [ ] action id：\n- [ ] preconditions：\n- [ ] postconditions：\n- [ ] requires：\n\n")

    state["last_at"] = rows[-1]["at"]
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print("生成 %s（%d 条），游标推进到 %s" % (out, len(rows), state["last_at"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
