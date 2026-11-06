#!/usr/bin/env bash
# 编译 fcitx4 官方 mb2txt（二进制码表 → 文本），用于回读校验。
# 用法: ./build_mb2txt.sh
# 产出: ./mb2txt
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
cd "$HERE"

mkdir -p im/table
cp -f tabledict.h im/table/tabledict.h

# 官方源码只在缺失时下载
if [ ! -f mb2txt.c ]; then
    curl -fsSL -o mb2txt.c \
        https://raw.githubusercontent.com/fcitx/fcitx/master/tools/cli/mb2txt.c
fi

gcc -O2 -I. -o mb2txt mb2txt.c stub.c
echo "已生成: $HERE/mb2txt"
echo "用法: ./mb2txt <码表.mb> > out.txt     或者加 -o 处理旧格式（version<3）"
