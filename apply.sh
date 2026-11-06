#!/usr/bin/env bash
# 用「已构建好的新码表」替换当前 fcitx 词库：停服 → 备份 → 全量校验 → 替换 → 重启。
# 用法: ./apply.sh <new_table.mb> [before.txt]
#   new_table.mb : merge_*.py 生成的新码表
#   before.txt   : 可选，替换前的 mb2txt 导出（不给则用当前词库现导）
set -euo pipefail

NEW=${1:?用法: ./apply.sh <new_table.mb> [before.txt]}
HERE=$(cd "$(dirname "$0")" && pwd)
MB="$HOME/.config/fcitx/table/wbpy.mb"
BEFORE=${2:-$HERE/before.txt}

[ -x "$HERE/mb2txt" ] || { echo "缺少 mb2txt，先跑 ./build_mb2txt.sh"; exit 1; }

# 1) 停 fcitx —— 它退出时会把内存表（含用户造词）写回 .mb，必须先停
pkill -TERM -x fcitx 2>/dev/null || true
sleep 3

# 2) 备份（关键）
TS=$(date +%Y%m%d-%H%M%S)
cp -p "$MB" "$HOME/wbpy.mb.bak-$TS"
echo "备份: ~/wbpy.mb.bak-$TS"

# 3) 基线（若未提供）
if [ ! -f "$BEFORE" ]; then
    "$HERE/mb2txt" "$MB" > "$BEFORE"
fi

# 4) 回读新表并全量比对
"$HERE/mb2txt" "$NEW" > "$HERE/after.txt"
ADD=$(diff <(sort "$BEFORE") <(sort "$HERE/after.txt") | grep -c '^>' || true)
LOST=$(diff <(sort "$BEFORE") <(sort "$HERE/after.txt") | grep -c '^<' || true)
echo "校验: 新增 $ADD 行 / 丢失 $LOST 行"
if [ "$LOST" != "0" ]; then
    echo "!! 检出记录丢失，已中止（原词库未改动）"
    exit 1
fi

# 5) 替换并启动
cp "$NEW" "$MB"
chmod 600 "$MB"
setsid fcitx -d >"$HERE/fcitx.log" 2>&1 < /dev/null &
sleep 5
ps -eo pid,cmd | grep "[f]citx -d" || echo "警告: fcitx 未启动，请检查 DISPLAY/XAUTHORITY/DBUS 环境变量"
echo "安装后条数: $("$HERE/mb2txt" "$MB" | wc -l)"
grep -i error "$HERE/fcitx.log" | grep -iv "already exists" || echo "启动日志无表相关报错"
