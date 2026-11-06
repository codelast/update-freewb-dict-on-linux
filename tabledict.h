#ifndef TABLEDICT_H
#define TABLEDICT_H
/* 极简头文件：只提供 fcitx4 tools/cli/mb2txt.c 需要的常量与函数声明。
 * 目的是把官方 mb2txt.c 单独编译出来，用于读写校验，无需整套 fcitx 开发环境。 */
#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>

#define MAX_CODE_LENGTH 30
#define UTF8_MAX_LENGTH 6

#define RECORDTYPE_NORMAL    0x0
#define RECORDTYPE_PINYIN    0x1
#define RECORDTYPE_CONSTRUCT 0x2
#define RECORDTYPE_PROMPT    0x3

typedef bool boolean;

int fcitx_utils_read_uint32(FILE* fp, uint32_t* out);

#endif /* TABLEDICT_H */
