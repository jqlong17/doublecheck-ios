#!/usr/bin/env python3
"""ops —— 能签字的运维动作。

每个动作是一份 YAML：前置条件 + 步骤 + 后置断言 + 回滚。
设计原则：**没有前置条件的动作不许合并**，没有后置断言的动作等于没做完。

用法：
  ops.py list
  ops.py lint                 校验所有动作（CI 用）
  ops.py plan <action> [k=v]  只评估前置条件，不执行任何步骤
  ops.py call <action> [k=v] [--yes]
  ops.py verify <action> [k=v]  只跑后置断言
"""
import glob
import json
import os
import re
import shutil
import socket
import ssl
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
ACTIONS = os.path.join(ROOT, "actions")

try:
    import yaml
except ImportError:  # pragma: no cover
    print("需要 PyYAML：pip3 install pyyaml", file=sys.stderr)
    raise SystemExit(2)


# ---------------- 参数替换 ----------------
def fill(value, params):
    if isinstance(value, str):
        return re.sub(r"\{\{(\w+)\}\}", lambda m: str(params.get(m.group(1), "")), value)
    if isinstance(value, list):
        return [fill(v, params) for v in value]
    if isinstance(value, dict):
        return {k: fill(v, params) for k, v in value.items()}
    return value


# ---------------- 断言/步骤实现 ----------------
def _run(cmd, timeout=10):
    try:
        p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True,
                           timeout=timeout)
        return p.returncode, (p.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return 124, "超时"


def p_unit_exists(spec):
    rc, out = _run("busctl call org.freedesktop.systemd1 /org/freedesktop/systemd1 "
                   "org.freedesktop.systemd1.Manager GetUnit s %s" % spec["unit"])
    return rc == 0, "unit %s %s" % (spec["unit"], "存在" if rc == 0 else "不存在")


def p_systemd_active(spec):
    rc, out = _run("busctl get-property org.freedesktop.systemd1 "
                   "/org/freedesktop/systemd1/unit/%s org.freedesktop.systemd1.Unit ActiveState"
                   % spec["unit"].replace("-", "_2d").replace(".", "_2e"))
    ok = rc == 0 and 's "active"' in out
    return ok, out[:80] or "查询失败"


def p_port_listening(spec):
    port = int(spec["port"])
    rc, out = _run("ss -lntu | awk '{print $5}' | grep -q ':%d$'" % port)
    return rc == 0, "端口 %d %s" % (port, "在听" if rc == 0 else "没有监听")


def p_port_free(spec):
    ok, msg = p_port_listening(spec)
    return (not ok), ("端口 %d 空闲" % spec["port"] if not ok else "端口 %d 被占用" % spec["port"])


def p_http_status(spec):
    url = spec["url"]
    expect = spec.get("expect", [200])
    timeout = spec.get("timeout_s", 8)
    try:
        req = urllib.request.Request(url, method=spec.get("method", "GET"))
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code = r.getcode()
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:  # noqa: BLE001
        return False, "请求失败: %s" % str(e)[:60]
    return code in expect, "HTTP %d（期望 %s）" % (code, expect)


def p_disk_free_mb_gt(spec):
    path = spec.get("path", "/")
    need = int(spec["mb"])
    free_mb = shutil.disk_usage(path).free // (1024 * 1024)
    return free_mb > need, "%s 剩余 %dMB（要求 >%d）" % (path, free_mb, need)


def p_file_exists(spec):
    ok = os.path.exists(spec["path"])
    return ok, "%s %s" % (spec["path"], "存在" if ok else "不存在")


def p_cert_expiry_days(spec):
    host, port = spec["host"], int(spec.get("port", 443))
    days = int(spec.get("days", 14))
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert()
        exp = ssl.cert_time_to_seconds(cert["notAfter"])
        left = int((exp - time.time()) // 86400)
        return left >= days, "%s 证书剩 %d 天（要求 >=%d）" % (host, left, days)
    except Exception as e:  # noqa: BLE001
        return False, "取证书失败: %s" % str(e)[:60]


def p_tls_hostname(spec):
    host, port = spec["host"], int(spec.get("port", 443))
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert()
        ssl.match_hostname(cert, host)
        return True, "证书匹配 %s" % host
    except Exception as e:  # noqa: BLE001
        return False, "证书不匹配或握手失败: %s" % str(e)[:60]


def p_cmd_exit0(spec):
    rc, out = _run(spec["run"], timeout=spec.get("timeout_s", 30))
    return rc == 0, (out.splitlines()[-1][:90] if out else "退出码 %d" % rc)


PREDICATES = {
    "unit.exists": p_unit_exists,
    "systemd.active": p_systemd_active,
    "port.listening": p_port_listening,
    "port.free": p_port_free,
    "http.status": p_http_status,
    "disk.free_mb_gt": p_disk_free_mb_gt,
    "file.exists": p_file_exists,
    "cert.expiry_days": p_cert_expiry_days,
    "tls.hostname_matches": p_tls_hostname,
    "cmd.exit0": p_cmd_exit0,
}


def s_systemd(spec):
    action = spec.get("op", "restart")
    rc, out = _run("busctl call org.freedesktop.systemd1 /org/freedesktop/systemd1 "
                   "org.freedesktop.systemd1.Manager %sUnit ss %s replace"
                   % (action.capitalize(), spec["unit"]), timeout=30)
    return rc == 0, out[:80]


def s_cmd(spec):
    rc, out = _run(spec["run"], timeout=spec.get("timeout_s", 60))
    return rc == 0, (out.splitlines()[-1][:90] if out else "退出码 %d" % rc)


def s_prune(spec):
    """只删白名单目录里的内容，且先算大小。"""
    removed = 0
    for path in spec.get("paths", []):
        if not os.path.isdir(path):
            continue
        for name in os.listdir(path):
            full = os.path.join(path, name)
            try:
                size = os.path.getsize(full) if os.path.isfile(full) else 0
                if os.path.isdir(full):
                    shutil.rmtree(full)
                else:
                    os.remove(full)
                removed += size
            except OSError:
                pass
    return True, "清理约 %.1f MB" % (removed / 1048576.0)


def s_noop(spec):
    return True, "（只读动作，无步骤）"


STEPS = {
    "noop": s_noop,
    "systemd.restart": s_systemd,
    "systemd.start": s_systemd,
    "cmd.run": s_cmd,
    "fs.prune": s_prune,
}


# ---------------- 加载与校验 ----------------
def load_actions():
    """动作放在 actions/<domain>/<name>.yaml；domain 由目录推导，避免和字段写不一致。"""
    out = []
    for path in sorted(glob.glob(os.path.join(ACTIONS, "*", "*.yaml"))):
        with open(path, encoding="utf-8") as f:
            d = yaml.safe_load(f)
        d["_path"] = path
        d["domain"] = os.path.basename(os.path.dirname(path))
        out.append(d)
    return out


REQUIRED = ["schemaVersion", "action", "summary", "incident", "preconditions", "steps", "postconditions"]
ALLOWED_REQUIRES = {"linux", "macos", "xcode", "keychain", "network", "systemd"}


def lint_one(d):
    errs = []
    for k in REQUIRED:
        if k not in d:
            errs.append("缺少字段 %s" % k)
    if not str(d.get("incident", "")).strip():
        errs.append("incident 为空（每个动作必须能追溯到一次真实事故或需求）")
    for group in ("preconditions", "postconditions"):
        for i, item in enumerate(d.get(group) or []):
            kind = item.get("kind")
            if kind not in PREDICATES:
                errs.append("%s[%d] 未知断言 %r" % (group, i, kind))
    for i, item in enumerate(d.get("steps") or []):
        if item.get("kind") not in STEPS:
            errs.append("steps[%d] 未知步骤 %r" % (i, item.get("kind")))
    if not (d.get("steps") or []):
        errs.append("没有步骤")
    if not (d.get("postconditions") or []):
        errs.append("没有后置断言——做完无法判定成功")
    for r in (d.get("requires") or []):
        if r not in ALLOWED_REQUIRES:
            errs.append("未知 requires: %r" % r)
    fx = d.get("fixture") or {}
    for k in ("dirty", "clean"):
        if k in fx and not os.path.isdir(fx[k]):
            errs.append("fixture.%s 路径不存在: %s" % (k, fx[k]))
    return errs


# ---------------- 执行 ----------------
QUIET = False


def check_all(items, params, title, collect=None):
    if not QUIET:
        print("  %s：" % title)
    ok_all = True
    for item in items:
        spec = fill(item, params)
        fn = PREDICATES[spec["kind"]]
        t0 = time.time()
        try:
            ok, msg = fn(spec)
        except Exception as e:  # noqa: BLE001
            ok, msg = False, "异常: %s" % e
        ms = int((time.time() - t0) * 1000)
        if not QUIET:
            print("    %s %-28s %s (%dms)" % ("✅" if ok else "❌", spec["kind"], msg, ms))
        if collect is not None:
            collect.append({"kind": spec["kind"], "ok": bool(ok), "msg": msg, "ms": ms})
        ok_all = ok_all and ok
    return ok_all


def do_plan(d, params, as_json=False):
    global QUIET
    QUIET = as_json
    collected = []
    if as_json:
        ok = check_all(d["preconditions"], params, "前置条件", collected)
        print(json.dumps({"action": d["action"], "domain": d.get("domain"), "ok": ok, "checks": collected,
                          "steps": [fill(x, params) for x in d["steps"]],
                          "rollback": [fill(x, params) for x in (d.get("rollback") or [])]},
                         ensure_ascii=False))
        return 0 if ok else 1
    print("动作：%s" % d["action"])
    print("  %s" % d["summary"])
    print("  来源：%s" % str(d["incident"]).strip().splitlines()[0][:100])
    ok = check_all(d["preconditions"], params, "前置条件")
    print("  将执行：")
    for s in d["steps"]:
        spec = fill(s, params)
        print("    - %s %s" % (spec["kind"], {k: v for k, v in spec.items() if k != "kind"}))
    if d.get("rollback"):
        print("  回滚：")
        for s in d["rollback"]:
            spec = fill(s, params)
            print("    - %s %s" % (spec["kind"], {k: v for k, v in spec.items() if k != "kind"}))
    print("  结论：%s" % ("可以执行" if ok else "前置条件不满足，不要执行"))
    return 0 if ok else 1


def do_call(d, params, yes):
    if do_plan(d, params) != 0:   # 注意：0 才是通过（之前的 not 判断反了，一执行就中止）
        print("中止：前置条件不满足")
        return 1
    if not yes:
        print("\n（演练模式）加 --yes 才会真正执行步骤")
        return 0
    print("\n执行步骤：")
    for s in d["steps"]:
        spec = fill(s, params)
        ok, msg = STEPS[spec["kind"]](spec)
        print("  %s %s %s" % ("✅" if ok else "❌", spec["kind"], msg))
        if not ok:
            if d.get("rollback"):
                print("  触发回滚：")
                for r in d["rollback"]:
                    rs = fill(r, params)
                    rok, rmsg = STEPS[rs["kind"]](rs)
                    print("    %s %s %s" % ("✅" if rok else "❌", rs["kind"], rmsg))
            return 1
    print("\n后置断言：")
    ok = check_all(d["postconditions"], params, "验证结果")
    print("  结论：%s" % ("成功" if ok else "步骤跑完但断言没过——按失败处理"))
    return 0 if ok else 1


def do_verify(d, params, as_json=False):
    global QUIET
    QUIET = as_json
    collected = []
    ok = check_all(d["postconditions"], params, "后置断言", collected)
    if as_json:
        print(json.dumps({"action": d["action"], "domain": d.get("domain"), "ok": ok, "checks": collected}, ensure_ascii=False))
    return 0 if ok else 1


def build_fixture(src):
    """把 fixture 目录复制到临时目录，按 .fixture.yaml 建一个 git 仓库。"""
    import shutil as _sh
    import tempfile
    meta_path = os.path.join(src, ".fixture.yaml")
    meta = {}
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
    base = tempfile.mkdtemp(prefix="dc-fixture-")
    dst = os.path.join(base, "repo")
    _sh.copytree(src, dst)   # py3.6 没有 dirs_exist_ok，复制到不存在的子目录
    untracked = set(meta.get("untracked") or [])
    _run("cd %s && git init -q && git add -A" % dst)
    for u in untracked:
        _run("cd %s && git rm --cached -q --ignore-unmatch %s" % (dst, u))
    _run("cd %s && git -c user.name=fixture -c user.email=f@x commit -q -m init" % dst)
    return dst


def cmd_fixture_test(actions):
    """对声明了 fixture 的动作：在 dirty 上必须失败、在 clean 上必须通过。"""
    bad = checked = 0
    for d in actions:
        fx = d.get("fixture") or {}
        if not fx:
            continue
        checked += 1
        name = d["action"]
        dirty = [c for c in (d.get("postconditions") or [])]
        for label, path, expect_ok in (("dirty", fx["dirty"], False), ("clean", fx["clean"], True)):
            params = dict(d.get("params") or {})
            params["repo"] = build_fixture(path)
            ok = True
            for item in dirty:
                spec = fill(item, params)
                try:
                    got, _ = PREDICATES[spec["kind"]](spec)
                except Exception:  # noqa: BLE001
                    got = False
                ok = ok and got
            good = (ok == expect_ok)
            print("%-30s %-6s 期望%s 实际%s  %s" % (name, label, "通过" if expect_ok else "失败",
                                                  "通过" if ok else "失败", "✅" if good else "❌"))
            if not good:
                bad += 1
    print("\n%d 个动作带 fixture，%d 个用例不符合预期" % (checked, bad))
    return 0 if bad == 0 else 1


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = args[0]
    actions = load_actions()

    if cmd == "list":
        want = None
        for i, a in enumerate(args):
            if a == "--domain" and i + 1 < len(args):
                want = args[i + 1]
        cur = None
        for d in actions:
            if want and d.get("domain") != want:
                continue
            if d.get("domain") != cur:
                cur = d.get("domain")
                print("\n[%s]" % cur)
            print("  %-24s %s" % (d["action"], d["summary"]))
        return 0

    if cmd == "fixture-test":
        return cmd_fixture_test(actions)

    if cmd == "lint":
        bad = 0
        for d in actions:
            errs = lint_one(d)
            if errs:
                bad += 1
                print("❌ %s" % d.get("action", d["_path"]))
                for e in errs:
                    print("   - %s" % e)
            else:
                print("✅ %s" % d["action"])
        print("\n%d 个动作，%d 个有问题" % (len(actions), bad))
        return 0 if bad == 0 else 1

    if len(args) < 2:
        print("缺少动作名")
        return 2
    name = args[1]
    rest = args[2:]
    yes = "--yes" in rest
    as_json = "--json" in rest
    params = {}
    for a in rest:
        if "=" in a and not a.startswith("-"):
            k, v = a.split("=", 1)
            params[k] = v
    target = next((d for d in actions if d["action"] == name), None)
    if not target:
        print("找不到动作 %s" % name)
        return 2
    merged = {"ops_dir": ROOT}          # 内建参数：动作可以引用自己的脚本，跨机器部署也不会写死路径
    merged.update(target.get("params") or {})
    merged.update(params)
    params = merged

    if cmd == "plan":
        return do_plan(target, params, as_json)
    if cmd == "call":
        return do_call(target, params, yes)
    if cmd == "verify":
        return do_verify(target, params, as_json)
    print("未知命令 %s" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
