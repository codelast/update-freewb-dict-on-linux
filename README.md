# update-freewb-dict-on-linux

在 Linux 上安全地扩充「极点五笔」词库的一套小工具 —— 面向 **fcitx 4.x + `fcitx-table-wbpy`**（「五笔拼音」码表）用户。

> 提供该二进制码表格式的**无损读写**、外部词库合并、候选词质量筛选，以及「停输入法 → 备份 → 重建 → 官方工具全量校验 → 替换 → 重启」的上线流程和一键回滚。

## 背景

Linux 上没有 Windows 版极点五笔，「极点」的体验实际由 fcitx 的码表引擎 + `wbpy` 码表提供，词库是位于 `~/.config/fcitx/table/wbpy.mb` 的**二进制文件**（几十万条、十几 MB）。它的问题在于：

- 没有任何官方编辑器，用文本工具改必然损坏（轻则加载失败，重则能启动但查不到词）；
- 现成的转换工具多数只能**读**不能**写**，其中有的实现连字段宽度都判断错了（见[常见问题](#常见问题)）；
- 词库内容停留在 2010 年代，新词、网络用语、专有名词大量缺失。

本项目补上这几块：读写格式、合并新词、筛掉噪音、并且在动你的线上词库之前**用 fcitx 自己的 `mb2txt` 做一次全量比对**。

## 特性

- fcitx4 码表（`.mb`，内部版本 3）的**无损解析与序列化**
- 插入词条时**可控制候选位置**（默认插到同码组末尾，即候选最后一位）
- 支持写入拼音记录，含**多音字备选读音**，且读音以「你词库里已存在的单字读音」为白名单
- 候选筛选流水线：语料词频 + **PMI（内部凝固度）** + 虚词/短语黑名单 + 词典交叉验证
- 安全上线：停输入法 → 备份 → 基于最新文件重建 → 全量 diff 校验 → 替换 → 重启
- 一键回滚；**不需要 root，不改动任何系统文件**

## 环境要求

| 项目             | 说明                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| 系统             | Linux + **fcitx 4.x** + `fcitx-table-wbpy`                   |
| 编译             | `gcc`、`curl`（用于编译 fcitx 官方 `mb2txt`）                  |
| Python           | 3.8+；只有生成拼音码时需要 `pypinyin`（`pip install pypinyin`）  |
| **不支持** | fcitx5（用的是 libime 的 `*.main.dict`）、IBus、Windows 版极点五笔 |

## 快速开始

```bash
git clone <本仓库> && cd update-freewb-dict-on-linux
./build_mb2txt.sh                                # 编译官方 mb2txt（源码从 fcitx/fcitx 现取）

DICT="$HOME/.config/fcitx/table/wbpy.mb"
./mb2txt "$DICT" > dump.txt                      # 基线：现有词条 + 单字码 / 单字读音

# 1) 生成候选（CSV：词,五笔码,词频,...）
#    chars.dict.yaml / words.dict.yaml 来自 rime-frost 的 cn_dicts_wb/（见「数据来源」）
python3 filter_candidates.py dump.txt chars.dict.yaml words.dict.yaml > cand.csv

# 2) 并入五笔词条（CSV 列：词,五笔码）
python3 merge_wubi.py "$DICT" cand.csv new.mb

# 3) 可选：补拼音记录（CSV 列：词,拼音码）
python3 gen_pinyin.py cand.csv py.csv dump.txt 4
python3 merge_pinyin.py "$DICT" py.csv new.mb

# 4) 上线：停 fcitx → 备份 → 校验（丢失必须为 0）→ 替换 → 重启
./apply.sh new.mb dump.txt

# 5) 发现异常就回滚
./rollback.sh ~/wbpy.mb.bak-YYYYmmdd-HHMMSS
```

装完后切到「五笔拼音」，打几个新增的编码 / 拼音确认。

## 文件说明

| 文件                        | 作用                                                                 | 用法                                                                       |
| --------------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `build_mb2txt.sh`         | 编译 fcitx 官方 `mb2txt`（二进制 → 文本）                         | `./build_mb2txt.sh`                                                      |
| `tabledict.h`、`stub.c` | 单独编译 `mb2txt.c` 所需的极简头文件与一个符号的 stub              | 由上面的脚本调用                                                           |
| `mb_table.py`             | **格式读写库**：`read()` / `write()` / `insert_sorted()` | `import mb_table`                                                        |
| `merge_wubi.py`           | 并入五笔词条（`type=0`）                                           | `merge_wubi.py <源.mb> <候选.csv> <输出.mb>`                             |
| `gen_pinyin.py`           | 生成拼音码（含多音备选）                                             | `gen_pinyin.py <词表.csv> <输出.csv> <dump.txt> [每词最多码数]`          |
| `merge_pinyin.py`         | 并入拼音记录（`type=1`），支持跳过冲突码                           | `merge_pinyin.py <源.mb> <拼音.csv> <输出.mb> [跳过的码,...]`            |
| `filter_candidates.py`    | 候选筛选（差集 + PMI + 黑名单）                                      | `filter_candidates.py <dump.txt> <chars.dict.yaml> <词库...> > cand.csv` |
| `apply.sh`                | 停服 → 备份 → 校验 → 替换 → 重启                                 | `apply.sh <新表.mb> [before.txt]`                                        |
| `rollback.sh`             | 回滚到备份并重启                                                     | `rollback.sh <备份文件>`                                                 |

## 原理：码表格式与四条硬约束

格式是从 fcitx4 源码逆向确认的（`src/im/table/tabledict.c`、`tools/cli/mb2txt.c`、`tools/cli/txt2mb.c`）：

```
头部：u32 0 | i8 版本(3) | u32 keyLen | KeyCode[keyLen+1]
      | u8 码长 | u8 拼音码长 | u32 忽略字符长度 | InvalidChar[+1]
      | u8 是否有组词规则 | (码长-1) × [flag, words, 码长 × (flag, which, index)]
      | u32 记录数
记录：码[拼音码长+1]   ← 注意不是「码长+1」
      | u32 词长（含结尾 NUL） | 词（UTF-8 + NUL）
      | i8 类型（0=五笔 1=拼音 2=自造词 3=提示）
      | u32 iHit（用户命中次数） | u32 iIndex（全局递增序号）
```

四条必须遵守的约束：

1. **记录按「码的首字节」分组排序**。fcitx 靠 `cChar != strCode[0]` 建索引，顺序乱了就查不到。
2. **候选顺序 = 文件里的记录顺序**。想让新词排在同码组最后，就插到组尾（`insert_sorted` 的默认行为）；想排第一就插到组首。
3. `iIndex` 取「现有最大值 + 1」，`iHit` 新词写 0。
4. **fcitx 退出时会重写整个 `.mb`**（把内存里的表连同用户造词落盘）。所以必须「先停、再备份、再基于它留下的文件重建」。

校验不依赖我们自己的解析器：`apply.sh` 会用 fcitx 的 `mb2txt` 分别回读旧表和新表，**diff 里丢失为 0 才允许替换线上文件**。

## 候选筛选方法

拼音词库是为**整句解码**服务的，天然塞满 `有多`、`人是`、`的时候` 这类高频二元组 —— 对拼音有意义，对四码形码输入是纯噪音。`filter_candidates.py` 依次做五件事：

1. **差集**：去掉你词库里已有的词。
2. **编码可行性**：用**你自己的单字全码**按五笔词组规则拼词码（2 字=各前两码；3 字=首字首码+次字首码+末字前两码；4 字以上=前三字首码+末字首码）。
3. **PMI（内部凝固度）**：`log2(P(词) / Π P(字)) / (词长-1)`，阈值用**你词库已收录词的 PMI 分布**反推校准（实测 2 字词的 P25 ≈ 5.0）。
4. **黑名单分层**：虚词字、方位/副词短语形状（`…上/下/中`、`一直…`、`特别…`）、常见口语搭配。
5. **词典交叉**：把候选分成「确认是词」（在规范词表里）和「疑似新词/专名」，两档分别处理。

PMI 是必要条件而非充分条件（`的时候` 得分也很高），真正把噪音压下去的是后两层。**噪音预期**：2 字约 15%、3 字约 25~30%、4 字原始候选约 60% —— 建议人工过一遍清单头部。

## 数据来源与许可

本仓库**不含任何词库数据**，只处理你自己下载的文件：

| 来源                                                                                 | 许可证     | 用途                         |
| ------------------------------------------------------------------------------------ | ---------- | ---------------------------- |
| [gaboolic/rime-frost](https://github.com/gaboolic/rime-frost)（白霜）                 | GPL-3.0    | 词表 + 现代语料词频          |
| [gaboolic/rime-wubi-sentence](https://github.com/gaboolic/rime-wubi-sentence)（墨奇） | MIT        | 新词 / 专有名词              |
| [iDvel/rime-ice](https://github.com/iDvel/rime-ice)（雾凇，白霜上游）                 | GPL-3.0    | 间接继承                     |
| [pwxcoo/chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua)                     | MIT        | 成语白名单（4 字词）         |
| `现代汉语常用词表`（公开 gist）                                                    | 未声明许可 | 仅作「是否成词」判据         |
| [fcitx/fcitx](https://github.com/fcitx/fcitx)                                         | GPL-2.0    | 本地编译 `mb2txt.c` 作校验 |

**你产出的词库会继承上游条款。** 本机自用不涉及分发，没有合规义务；如果要把生成的 `.mb` 发布出去，GPL-3.0 部分需要提供生成脚本并沿用同一许可，MIT 部分保留版权声明。

## 安全须知

- 不需要 root；除 `~/.config/fcitx/table/`（词库与备份）和本目录外，不改动任何文件。
- 每次替换前都会生成带时间戳的备份；`apply.sh` 一旦发现 diff 有记录丢失就**中止，不动原库**。
- 三层验证：**结构**（`mb2txt` 全量 diff）、**加载**（`xprop -root | grep XIM_SERVERS` 应含 `@server=fcitx`，fcitx 日志无表相关报错）、**功能**（实打若干词：唯一码应直接上屏，重码词出现在候选末位）。
- `fcitx-remote` 在无输入焦点的终端里可能返回 0，**不能当健康检查**；以实际打字或 `xprop` 为准。

## 常见问题

**为什么不用 `txt2mb`？** fcitx4 源码里确实有，但主流发行版都不打包，且需要完整 fcitx 编译环境。本项目不需要它：序列化由自己完成，只把 `mb2txt`（极易单独编译）当**独立校验器**。

**为什么不用 `nopdan/rose` 的 `fcitx4_mb` 解析器？** 它假设码字段宽度是 `码长 + 1`，真实是**拼音码长 + 1**（`wbpy` 表里是 13）。按错误宽度解析会整体错位一条记录，且不报错；而且它只支持导入。

**能用于其它码表吗（如 `wbx`、`wubi86`）？** 可以，只要是 fcitx **4** 的码表（版本 3）。把码表路径显式传给 `merge_*.py` 即可。

**怎么让新词排在同码组第一位？** 改成插到组首（见 `insert_sorted`）。

**拼音码为什么被截断到 12 个字母？** 那是表头里的拼音码长。不影响使用：fcitx 是**前缀匹配**（`ExactMatch=False`），打到前几个字母就能出候选。

**会原地修改我的词库吗？** 会 —— `apply.sh` 替换的就是 `~/.config/fcitx/table/wbpy.mb`。所以务必备份，脚本会打印备份路径。

## 许可证

本仓库代码：**MIT** —— 发布前请自行添加 `LICENSE` 文件（可从 [https://choosealicense.com/licenses/mit/](https://choosealicense.com/licenses/mit/) 生成）并填上你的版权行。

仓库内不包含任何来自 fcitx 的代码；校验用的 `mb2txt.c` 在构建时从上游下载，其许可证为 **GPL-2.0**。你生成的词库可能继承第「数据来源与许可」一节所列的条款。

## 致谢

- fcitx / fcitx-table：格式定义与官方工具
- gaboolic：白霜（rime-frost）与墨奇（rime-wubi-sentence）
- pwxcoo：成语语料；pypinyin：读音
- 极点五笔（FreeWB）作者与极爽词库维护者 —— 这套生态的词汇基础

## 免责声明

按「现状」提供，不附带任何担保。你要修改的是**正在使用的输入法词库**：请先备份、先看 diff、先用几个词试打，再决定是否长期使用。筛选是启发式的，清单头部请自己过一眼。
