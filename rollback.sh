#!/usr/bin/env bash
# 回滚到指定备份并重启 fcitx。
# 用法: ./rollback.sh ~/wbpy.mb.bak-YYYYmmdd-HHMMSS
set -euo pipefail

BK=${1:?用法: ./rollback.sh <备份文件>}
MB="$HOME/.config/fcitx/table/wbpy.mb"

[ -f "$BK" ] || { echo "备份不存在: $BK"; exit 1; }

pkill -TERM -x fcitx 2>/dev/null || true
sleep 2
cp -p "$BK" "$MB"
chmod 600 "$MB"
setsid fcitx -d >/dev/null 2>&1 < /dev/null &
sleep 3
if ps -eo pid,cmd | grep -q "[f]citx -d"; then
    echo "已回滚并重启: $BK"
else
    echo "已回滚，但 fcitx 未启动，请手动执行: fcitx -d"
fi
