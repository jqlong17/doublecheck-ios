#!/bin/bash
# 贡献闸门：lint 全部通过 + 只读动作真的能跑通 + 变更动作只演练不执行。
set -uo pipefail
cd "$(dirname "$0")/.."
fail=0

echo "== 1/2 lint =="
python3 ops.py lint || fail=1

echo
echo "== 2/2 每个动作 =="
for f in actions/*/*.yaml; do
  a=$(basename "$f" .yaml)
  printf '%-18s ' "$a"
  if ! python3 ops.py plan "$a" >/dev/null 2>&1; then
    echo "❌ plan 失败（前置条件不满足或动作有误）"
    fail=1
    continue
  fi
  if grep -q "^fixture:" "$f"; then
    echo "✅ plan 通过（fixture 阶段验证）"
  elif grep -q "repo:" "$f"; then
    echo "✅ plan 通过（依赖目标仓库，由使用者本机执行）"
  elif grep -qE "kind: (systemd\.restart|systemd\.start|fs\.prune|cmd\.run)" "$f"; then
    echo "✅ plan 通过（变更类动作，不执行）"
  else
    if python3 ops.py verify "$a" >/dev/null 2>&1; then
      echo "✅ plan + verify 通过"
    else
      echo "❌ verify 失败"
      fail=1
    fi
  fi
done

echo
echo "== 3/3 fixture（dirty 必须失败 / clean 必须通过）=="
python3 ops.py fixture-test || fail=1

echo
if [ "$fail" = "0" ]; then echo "CI 通过"; else echo "CI 失败"; fi
exit $fail
