#!/usr/bin/env python3
"""docs/ 是否允许入库——这是项目策略，不是客观对错。

配置写在仓库根的 .doublecheck.yaml：

    version: 1
    policies:
      docs.tracked: forbid    # forbid（默认）/ allow

没配置时**不检查、不报错**，只提示一句：我们不该替你决定仓库怎么组织。
"""
import os
import sys

repo = sys.argv[1] if len(sys.argv) > 1 else "."
cfg_path = os.path.join(repo, ".doublecheck.yaml")

mode = None
if os.path.exists(cfg_path):
    try:
        import yaml
        cfg = yaml.safe_load(open(cfg_path, encoding="utf-8")) or {}
        mode = ((cfg.get("policies") or {}).get("docs") or {}).get("tracked")
    except Exception as e:  # noqa: BLE001
        print("读 .doublecheck.yaml 失败：%s" % e)
        sys.exit(2)

if mode is None:
    print("未配置策略（.doublecheck.yaml: policies.docs.tracked），跳过")
    sys.exit(0)
if mode == "allow":
    print("策略：允许 docs/ 入库，跳过")
    sys.exit(0)

os.execvp("bash", ["bash", os.path.join(os.path.dirname(__file__), "ios-guard.sh"), "docs-leak", repo])
