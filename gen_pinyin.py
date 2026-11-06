#!/usr/bin/env python3
"""为词表生成拼音码（含多音备选）。
用法: gen_pinyin.py <词表.csv(含"词"列)> <输出.csv> <表dump.txt> [每词最多几个码]

要点：
1) 用 pypinyin，词组级注音（避免多音字按单字乱读）；
2) 多音备选：heteronym=True 组合出候选，但**只保留表里已出现过的单字读音**；
3) 按表的 pyCodeLen 截断（示例 12）——前缀匹配所以不影响使用。
"""
import sys, csv, itertools, collections
from pypinyin import lazy_pinyin, pinyin, Style

words_csv, out_csv, dump = sys.argv[1], sys.argv[2], sys.argv[3]
cap = int(sys.argv[4]) if len(sys.argv) > 4 else 4

# 1) 表里已有的单字读音（作为读音白名单）
local = collections.defaultdict(set)
lines = open(dump, encoding='utf-8').read().split('\n')
body = lines[lines.index('[Data]') + 1:]
for ln in body:
    if ln.startswith('@') and ' ' in ln:
        c, w = ln[1:].split(' ', 1)
        if len(w) == 1:
            local[w].add(c)

rows = []
for r in csv.DictReader(open(words_csv, encoding='utf-8')):
    w = (r.get('词') or '').strip()
    if not w:
        continue
    base = ''.join(lazy_pinyin(w))[:12]
    if not base:
        continue
    cands = [base]
    vs = pinyin(w, heteronym=True, style=Style.NORMAL)
    # 每个字只保留表里出现过的读音，否则用原读音集合
    vs = [[p for p in lst if p in local.get(ch, {p})] or lst for lst, ch in zip(vs, w)]
    for combo in itertools.product(*vs):
        p = ''.join(combo)[:12]
        if p not in cands:
            cands.append(p)
        if len(cands) >= cap:
            break
    for i, p in enumerate(cands[:cap]):
        rows.append((w, p, 'primary' if i == 0 else 'variant'))

with open(out_csv, 'w', newline='', encoding='utf-8') as f:
    wr = csv.writer(f); wr.writerow(['词', '拼音码', '类型']); wr.writerows(rows)
print(f'词 {len(rows)} 行，主读音/多音见文件')
