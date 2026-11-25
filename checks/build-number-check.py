#!/usr/bin/env python3
"""检查某个 build 号是否已经在 App Store Connect 里用过。

用法：
  python3 build-number-check.py --repo <路径> [--build N]

退出码：
  0  未被占用（可以上传）
  1  已存在（上传会被判 INVALID_BINARY）
  2  无法完成检查（缺凭据 / 网络 / 应用找不到）

凭据来自环境变量（zshrc 里已有）：
  ASC_KEY_ID / ASC_PRIVATE_KEY_PATH / ASC_ISSUER_ID
应用 id 从仓库 Info.plist 读不到，默认用 DSHPocket 的 6832288744，可用 ASC_APP_ID 覆盖。
"""
import argparse
import base64
import json
import os
import plistlib
import subprocess
import sys
import time
import urllib.request


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def der_to_raw(sig):
    """ECDSA DER (30 len 02 lenR R 02 lenS S) → 64 字节 r||s。

    不能用 sig[-64:]：r/s 可能带前导 0x00，长度会变，直接截断会签出无效 JWT。
    """
    i = 2 if sig[1] < 0x80 else 3
    assert sig[i] == 0x02
    rlen = sig[i + 1]
    r = sig[i + 2:i + 2 + rlen]
    i2 = i + 2 + rlen
    assert sig[i2] == 0x02
    slen = sig[i2 + 1]
    s = sig[i2 + 2:i2 + 2 + slen]
    return r.lstrip(b"\x00").rjust(32, b"\x00") + s.lstrip(b"\x00").rjust(32, b"\x00")


def jwt(key_id, issuer, key_path):
    now = int(time.time())
    header = b64(json.dumps({"alg": "ES256", "kid": key_id, "typ": "JWT"}).encode())
    payload = b64(json.dumps({"iss": issuer, "iat": now, "exp": now + 900,
                              "aud": "appstoreconnect-v1"}).encode())
    signing_input = ("%s.%s" % (header, payload)).encode()
    der = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", key_path],
        input=signing_input, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout
    raw = der_to_raw(der)
    return "%s.%s.%s" % (header, payload, b64(raw))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--build", type=int)
    args = ap.parse_args()

    cfg = {}
    cfg_path = os.path.expanduser("~/.doublecheck/asc.json")
    if os.path.exists(cfg_path):
        try:
            cfg = json.load(open(cfg_path, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            cfg = {}

    key_id = os.environ.get("ASC_KEY_ID") or cfg.get("keyId")
    issuer = os.environ.get("ASC_ISSUER_ID") or cfg.get("issuerId")
    key_path = os.path.expanduser(os.environ.get("ASC_PRIVATE_KEY_PATH") or cfg.get("keyPath") or "")
    app_id = os.environ.get("ASC_APP_ID") or cfg.get("appId") or "6832288744"
    if not (key_id and issuer and os.path.exists(key_path)):
        print("无法检查：缺少 ASC 凭据（ASC_KEY_ID / ASC_ISSUER_ID / ASC_PRIVATE_KEY_PATH）")
        return 2

    build = args.build
    if build is None:
        plist = os.path.join(args.repo, "Info.plist")
        if not os.path.exists(plist):
            print("无法检查：找不到 Info.plist")
            return 2
        with open(plist, "rb") as f:
            info = plistlib.load(f)
        build = int(info.get("CFBundleVersion", "0") or 0)
    if not build:
        print("无法检查：没拿到 build 号")
        return 2

    try:
        token = jwt(key_id, issuer, key_path)
        url = ("https://api.appstoreconnect.apple.com/v1/builds"
               "?filter[app]=%s&limit=200&fields[builds]=version,processingState" % app_id)
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        data = json.loads(opener.open(req, timeout=20).read().decode())
    except Exception as e:  # noqa: BLE001
        print("无法检查：%s" % str(e)[:120])
        return 2

    existing = {int(b["attributes"]["version"]) for b in data.get("data", [])
                if str(b["attributes"].get("version", "")).isdigit()}
    if build in existing:
        print("build %d 已存在（历史上传过），请换一个 build 号，否则会判 INVALID_BINARY" % build)
        return 1
    print("build %d 未被占用，可以上传（已有 %d 个历史 build）" % (build, len(existing)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
