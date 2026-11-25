#!/usr/bin/env python3
"""dc ios check —— 把 iOS 域的动作按“什么时候跑”分组执行。

  --fast     提交前跑（只读、秒级）
  --build    构建后跑（含模拟器编译）
  --release  发版前跑（全部，含全新构建）

用法：
  dc ios check --fast [--repo <路径>]
"""
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ACTIONS = os.path.join(ROOT, "actions", "ios")
OPS = os.path.join(ROOT, "ops.py")

try:
    import yaml
except ImportError:
    print("需要 PyYAML", file=sys.stderr)
    raise SystemExit(2)


def load():
    out = []
    for path in sorted(glob.glob(os.path.join(ACTIONS, "*.yaml"))):
        with open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f)
        d["_path"] = path
        out.append(d)
    return out


ALIAS = {"fast": "commit", "all": "release"}


def tier_of(action, profile):
    """按生命周期阶段筛选：commit / build / test / release。"""
    stage = action.get("stage", "commit")
    if profile == "release":
        return True          # 发版前把所有阶段都跑一遍
    return stage == ALIAS.get(profile, profile)


def main():
    profile = "commit"
    repo = "."
    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a in ("--commit", "--build", "--test", "--release", "--fast"):
            profile = "commit" if a == "--fast" else a[2:]
        if a == "--repo" and i + 1 < len(args):
            repo = args[i + 1]

    if not glob.glob(os.path.join(repo, "*.xcodeproj")):
        print("当前目录不像 iOS 工程（没有 .xcodeproj）：%s" % os.path.abspath(repo))
        print("在仓库根目录执行，或用 --repo 指定路径")
        return 0

    actions = [a for a in load() if tier_of(a, profile)]
    if not actions:
        print("没有适用的动作")
        return 0

    print("doublecheck ios · %s · %d 项检查\n" % (profile, len(actions)))
    failed = []          # 不变式失败 → 阻断
    warned = []          # 策略失败 → 只提示（--strict 才阻断）
    strict = "--strict" in sys.argv[1:]
    for a in actions:
        # 只读动作（全是 noop 步骤）跑 verify；有实际步骤的必须真执行，否则等于自欺欺人
        read_only = all(st.get("kind") == "noop" for st in (a.get("steps") or []))
        mode = ["verify", "--json"] if read_only else ["call", "--yes", "--json"]
        r = subprocess.run([sys.executable, OPS, mode[0], a["action"], *mode[1:], "repo=" + repo],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           universal_newlines=True)
        import json as _json
        try:
            d = _json.loads(r.stdout.strip().splitlines()[-1])
            ok = d.get("ok")
            detail = " ; ".join(c["msg"] for c in d.get("checks", []) if not c["ok"]) or "通过"
        except Exception:  # noqa: BLE001
            ok, detail = False, r.stdout.strip()[-120:]
        kind = a.get("kind", "invariant")
        if ok:
            mark = "✅"
        elif kind == "policy":
            mark = "⚠️ "
        else:
            mark = "❌"
        print("%s %-26s %s" % (mark, a["action"], detail[:80]))
        if not ok:
            (warned if kind == "policy" else failed).append(a["action"])

    print()
    if warned:
        print("策略未通过 %d 项（不阻断，--strict 才阻断）：%s" % (len(warned), ", ".join(warned)))
    if strict:
        failed += warned
    if failed:
        print("失败 %d 项：%s" % (len(failed), ", ".join(failed)))
        print("提示：每条检查防的是哪次事故，见 actions/ios/<名字>.yaml 的 incident 字段")
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
