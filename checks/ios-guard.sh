#!/bin/bash
# iOS 仓库的机器检查集合（由 doublecheck 的 ios.* 动作调用）。
# 每一条都对应 AGENTS.md 里一条踩坑记录。
set -uo pipefail
REPO="${2:-${REPO:-$HOME/projects/dsh-pocket-ios}}"
cd "$REPO" || { echo "找不到仓库 $REPO"; exit 2; }

cmd="${1:-}"

case "$cmd" in
  pbxproj)
    # 新增的 .swift 必须已在 project.pbxproj 注册
    missing=0
    # 未跟踪(??) 和 已暂存新增(A) 都要检查——只查 ?? 会漏掉 git add 之后的状态
    for f in $(git status --porcelain | awk '$1=="??" || $1=="A"{print $2}' | grep '\.swift$'); do
      if ! grep -q "$(basename "$f")" DSHPocket.xcodeproj/project.pbxproj; then
        echo "未注册: $f"
        missing=1
      fi
    done
    [ "$missing" = 0 ] && echo "所有新增 swift 文件都已注册"
    exit $missing
    ;;
  arch)
    ./scripts/check-architecture.sh
    ;;
  fonts)
    # 硬性禁止：.system(size:) 硬编码字号。
    # 只看代码：行首注释里的示例不算（2026-11-25 实测被注释误判过一次）。
    raw=$(grep -rn '\.system(size:' DSHPocket DSHKit --include='*.swift' 2>/dev/null)
    hits=$(printf '%s\n' "$raw" | grep -v ':[0-9]*:[[:space:]]*//' | grep -v ':[0-9]*:[[:space:]]*\*' | sed '/^$/d')
    n=$(printf '%s\n' "$hits" | sed '/^$/d' | wc -l | tr -d ' ')
    if [ "$n" != "0" ]; then
      echo "发现 $n 处硬编码字号（已排除注释）："
      printf '%s\n' "$hits" | head -5
      exit 1
    fi
    echo "没有硬编码字号"
    ;;
  docs-leak)
    # docs/ 一律不入库
    n=$(git ls-files docs | wc -l | tr -d ' ')
    if [ "$n" != "0" ]; then
      echo "docs/ 下有 $n 个文件被纳入版本控制（应当 gitignore）"
      exit 1
    fi
    echo "docs/ 未被跟踪"
    ;;
  buildnumber)
    # 版本号与 App Store Connect 已有 build 是否重复（需要 API key，慢，默认不跑）
    echo "跳过：需要 ASC 凭据"
    ;;
  secrets)
    # 硬性禁止：公网地址、token、私钥进代码或日志
    hits=$(grep -rnE '(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----)' \
      --include='*.swift' --include='*.sh' --include='*.js' --include='*.py' --include='*.json' --include='*.yml' --include='*.yaml' \
      . 2>/dev/null | grep -v '/\.git/' || true)
    if [ -n "$hits" ]; then
      echo "发现疑似凭证："
      printf '%s\n' "$hits" | head -5
      exit 1
    fi
    echo "没有发现疑似凭证"
    ;;
  shell-vars)
    # $VAR 后面紧跟中文/全角标点时，bash 会把多字节字符算进变量名
    bad=0
    for f in $(git ls-files '*.sh' 2>/dev/null); do
      if python3 - "$f" <<'PY2'
import re, sys
src = open(sys.argv[1], encoding="utf-8", errors="ignore").read()
bad = [m.group(0) for m in re.finditer(r"\$[A-Za-z_][A-Za-z0-9_]*(?=[^\x00-\x7F])", src)]
if bad:
    print("%s: %s" % (sys.argv[1], bad[:3]))
sys.exit(1 if bad else 0)
PY2
      then :; else bad=1; fi
    done
    [ "$bad" = "0" ] && echo "shell 变量写法安全"
    exit $bad
    ;;
  *)
    echo "用法: ios-guard.sh {pbxproj|arch|fonts|docs-leak|secrets|shell-vars}"
    exit 2
    ;;
esac
