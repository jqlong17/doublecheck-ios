#!/bin/bash
# 通过 SSH 读取 Windows 基本信息（OS、开机时间、系统盘余量、内存）
set -uo pipefail
host="${1:-win}"
out=$(ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" \
  'powershell -NoProfile -Command "[Console]::OutputEncoding=[Text.Encoding]::UTF8; $os=Get-CimInstance Win32_OperatingSystem; $d=Get-PSDrive C; Write-Output (\"OS=\" + $os.Caption + \" build=\" + $os.Version); Write-Output (\"uptime_days=\" + [math]::Round(((Get-Date) - $os.LastBootUpTime).TotalDays,1)); Write-Output (\"disk_free_gb=\" + [math]::Round($d.Free/1GB,1)); Write-Output (\"mem_free_gb=\" + [math]::Round($os.FreePhysicalMemory/1MB,1))"' 2>&1) || {
  echo "无法连接 $host：$out"
  exit 2
}
printf '%s\n' "$out"
