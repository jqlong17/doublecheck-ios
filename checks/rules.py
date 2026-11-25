#!/usr/bin/env python3
"""执行 rulebook 里的一条规则。

用法：python3 checks/rules.py <rule-id> <repo> [k=v ...]
退出码：0 通过 / 1 违规 / 2 无法检查
"""
import glob
import os
import re
import subprocess
import sys


def sh(cmd, timeout=15):
    try:
        p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return 2, str(e)


def tracked(repo):
    rc, out = sh("cd %s && git ls-files" % repo, 20)
    return out.splitlines() if rc == 0 else []


def c_regex(repo, spec, params):
    files = []
    for pat in spec["glob"].split(","):
        files.extend(glob.glob(os.path.join(repo, pat.strip()), recursive=True))
    # 默认只看产品代码：docs/ 下是参考项目，Tests/ 里允许写 try! 之类的测试写法
    SKIP = ("/.git/", "/docs/", "/.build/", "/Pods/", "/build/", "/DerivedData/",
            "/vendor/", "/Carthage/", "/Tests/", "/UITests/")
    if spec.get("include_tests"):
        SKIP = tuple(k for k in SKIP if k not in ("/Tests/", "/UITests/"))
    files = [f for f in files if os.path.isfile(f) and not any(k in f + "/" for k in SKIP)]
    if not files:
        return 2, "没有匹配到文件（%s）" % spec["glob"]
    rx = re.compile(spec["pattern"])
    ex = re.compile(spec["exclude"]) if spec.get("exclude") else None
    hits = []
    for f in files:
        try:
            for i, line in enumerate(open(f, encoding="utf-8", errors="ignore"), 1):
                if ex and ex.search(line):
                    continue
                if rx.search(line):
                    hits.append("%s:%d: %s" % (os.path.relpath(f, repo), i, line.strip()[:80]))
        except Exception:  # noqa: BLE001
            continue
    if len(hits) > spec.get("max", 0):
        return 1, "命中 %d 处（上限 %d）：\n  %s" % (len(hits), spec.get("max", 0), "\n  ".join(hits[:5]))
    return 0, "未超过上限（%d/%d）" % (len(hits), spec.get("max", 0))


def c_file_present(repo, spec, params):
    for pat in spec["paths"]:
        if glob.glob(os.path.join(repo, pat), recursive=True):
            return 0, "存在（%s）" % pat
    return 1, "缺少文件：%s" % " / ".join(spec["paths"])


def c_file_absent(repo, spec, params):
    files = tracked(repo)
    bad = []
    for f in files:
        for pat in spec["paths"]:
            if re.fullmatch(pat.replace("**", ".*").replace("*", "[^/]*"), f):
                bad.append(f)
    if bad:
        return 1, "被跟踪：%s" % ", ".join(bad[:5])
    return 0, "没有匹配的跟踪文件"


def c_file_size(repo, spec, params):
    limit = spec["max_mb"] * 1024 * 1024
    big = []
    for f in tracked(repo):
        p = os.path.join(repo, f)
        if os.path.isfile(p) and os.path.getsize(p) > limit:
            big.append("%s (%.1fMB)" % (f, os.path.getsize(p) / 1048576.0))
    if big:
        return 1, "超大文件：%s" % ", ".join(big[:5])
    return 0, "没有超过 %dMB 的跟踪文件" % spec["max_mb"]


def c_command(repo, spec, params):
    cmd = spec["cmd"]
    for k, v in params.items():
        cmd = cmd.replace("{{%s}}" % k, v)
    rc, out = sh("cd %s && %s" % (repo, cmd), spec.get("timeout", 15))
    msg = out.strip().splitlines()[-1][:100] if out.strip() else ("退出码 %d" % rc)
    return (0 if rc == 0 else 1), msg


def _plist(repo):
    import plistlib
    path = os.path.join(repo, "Info.plist")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return plistlib.load(f)


def _build_setting(repo, name):
    """从 project.pbxproj 里取一个构建设置的值（取第一处）。"""
    import glob as _glob
    hits = _glob.glob(os.path.join(repo, "**/*.xcodeproj/project.pbxproj"), recursive=True)
    if not hits:
        return None
    text = open(hits[0], encoding="utf-8", errors="ignore").read()
    m = re.search(r"%s\s*=\s*([^;]+);" % name, text)
    if not m:
        return None
    return m.group(1).strip().strip('"')


def c_plist_match(repo, spec, params):
    info = _plist(repo)
    if info is None:
        return 2, "找不到 Info.plist"
    got = info.get(spec["key"])
    # Info.plist 里用 $(VAR) 引用构建设置时，等价于自动一致
    if isinstance(got, str) and got.startswith("$("):
        return 0, "%s 引用构建设置 %s，自动一致" % (spec["key"], got)
    want = _build_setting(repo, spec["build_setting"])
    if want is None:
        # 老工程把版本直接写在 Info.plist，没有对应构建设置，视为不适用
        return 0, "工程未使用 %s（版本直接写在 Info.plist），跳过" % spec["build_setting"]
    got = info.get(spec["key"])
    if str(got) != str(want):
        return 1, "%s 期望 %r，实际 %r" % (spec["key"], want, got)
    return 0, "%s = %s" % (spec["key"], got)


def c_plist_key_present(repo, spec, params):
    info = _plist(repo)
    if info is None:
        return 2, "找不到 Info.plist"
    if spec["key"] in info:
        return 0, "已声明 %s" % spec["key"]
    return 1, "Info.plist 缺少 %s" % spec["key"]


def c_plist_ats(repo, spec, params):
    info = _plist(repo)
    if info is None:
        return 2, "找不到 Info.plist"
    ats = info.get("NSAppTransportSecurity") or {}
    if ats.get("NSAllowsArbitraryLoads"):
        return 1, "NSAllowsArbitraryLoads = true，等于关闭 ATS"
    return 0, "没有开启任意加载"


def c_plist_usage(repo, spec, params):
    info = _plist(repo)
    if info is None:
        return 2, "找不到 Info.plist"
    # 只有真的用了对应 API 才要求用途说明
    rc, out = sh("cd %s && grep -rl --include='*.swift' --exclude-dir=docs --exclude-dir=Tests --exclude-dir=UITests -E '%s' DSHPocket DSHKit 2>/dev/null | head -1" % (repo, spec["api"]), 20)
    if rc != 0 or not out.strip():
        return 0, "未使用相关 API，跳过"
    if spec["key"] in info:
        return 0, "已声明 %s" % spec["key"]
    return 1, "代码使用了 %s，但 Info.plist 缺 %s" % (spec["api"], spec["key"])


def c_plist_bg_mode(repo, spec, params):
    info = _plist(repo)
    if info is None:
        return 2, "找不到 Info.plist"
    rc, out = sh("cd %s && grep -rl --include='*.swift' --exclude-dir=docs --exclude-dir=Tests --exclude-dir=UITests -E '%s' DSHPocket DSHKit 2>/dev/null | head -1" % (repo, spec["api"]), 20)
    if rc != 0 or not out.strip():
        return 0, "未使用相关 API，跳过"
    modes = info.get("UIBackgroundModes") or []
    if spec["mode"] in modes:
        return 0, "已声明后台模式 %s" % spec["mode"]
    return 1, "使用了 %s，但 UIBackgroundModes 缺 %s" % (spec["api"], spec["mode"])


def c_appicon_1024(repo, spec, params):
    hits = glob.glob(os.path.join(repo, "**/AppIcon.appiconset/Contents.json"), recursive=True)
    if not hits:
        return 1, "找不到 AppIcon.appiconset"
    for h in hits:
        text = open(h, encoding="utf-8", errors="ignore").read()
        if '"1024' in text or "1024x1024" in text or '"size" : "1024x1024"' in text:
            return 0, "发现 1024 图标声明"
    return 1, "AppIcon 里没有 1024 尺寸"


def c_git_tag_match(repo, spec, params):
    info = _plist(repo)
    if info is None:
        return 2, "找不到 Info.plist"
    ver = str(info.get("CFBundleShortVersionString") or "")
    rc, out = sh("cd %s && git tag --points-at HEAD" % repo, 10)
    tags = [t for t in out.split() if t]
    if not tags:
        return 0, "当前提交没有 tag（未发版，跳过）"
    if any(ver and ver in t for t in tags):
        return 0, "tag 与版本一致：%s" % ", ".join(tags)
    return 1, "版本 %s 与 tag %s 不一致" % (ver, ", ".join(tags))


CHECKERS = {
    "regex": c_regex,
    "file_present": c_file_present,
    "file_absent": c_file_absent,
    "file_size": c_file_size,
    "command": c_command,
    "plist_match": c_plist_match,
    "plist_key_present": c_plist_key_present,
    "plist_ats": c_plist_ats,
    "plist_usage": c_plist_usage,
    "plist_bg_mode": c_plist_bg_mode,
    "appicon_1024": c_appicon_1024,
    "git_tag_match": c_git_tag_match,
}


def main():
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import rulebook

    if len(sys.argv) < 3:
        print("用法: rules.py <rule-id> <repo> [k=v ...]")
        return 2
    rule_id, repo = sys.argv[1], sys.argv[2]
    params = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
    rule = next((r for r in rulebook.RULES if r["id"] == rule_id), None)
    if not rule:
        print("未知规则 %s" % rule_id)
        return 2
    fn = CHECKERS.get(rule["check"]["type"])
    if not fn:
        print("未知检查类型 %s" % rule["check"]["type"])
        return 2
    code, msg = fn(repo, rule["check"], params)
    print(("[%s] " % rule_id) + msg)
    return code


if __name__ == "__main__":
    sys.exit(main())
