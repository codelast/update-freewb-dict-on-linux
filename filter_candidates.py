#!/usr/bin/env python3
"""从外部词库产生候选清单。用法: filter_candidates.py <dump.txt> <chars.dict.yaml> <词库1> [词库2 ...] > cand.csv

流程：本机差集 → 编码可还原 → 虚词/短语过滤 → PMI 阈值 → 分档输出
"""
import sys, math, json, collections

dump = sys.argv[1]
lines = open(dump, encoding='utf-8').read().split('\n')
body = lines[lines.index('[Data]') + 1:]

local, wubi_single = set(), {}
for ln in body:
    if ' ' not in ln:
        continue
    if ln.startswith('@'):
        local.add(ln[1:].split(' ', 1)[1]); continue
    c, w = ln.split(' ', 1)
    local.add(w)
    if len(w) == 1 and c.isalpha() and len(c) > len(wubi_single.get(w, '')):
        wubi_single[w] = c                       # 单字五笔全码（取最长）

def word_code(w):
    """按五笔词组规则，用**本机单字码**拼词码（比信外部词库更一致）"""
    cs = [wubi_single.get(ch) for ch in w]
    if any(not c for c in cs):
        return None
    if len(w) == 2:  r = cs[0][:2] + cs[1][:2]
    elif len(w) == 3: r = cs[0][0] + cs[1][0] + cs[2][:2]
    elif len(w) >= 4: r = cs[0][0] + cs[1][0] + cs[2][0] + cs[-1][0]
    else: return None
    return r if len(r) == 4 and r.isalpha() else None

# 字频（用词库自带的单字表）
char, tot_c = {}, 0
for ln in open(sys.argv[2], encoding='utf-8'):        # chars.dict.yaml
    if ln.startswith('#') or '\t' not in ln: continue
    p = ln.rstrip('\n').split('\t')
    if len(p) >= 3 and p[2].isdigit():
        char[p[0]] = int(p[2]); tot_c += int(p[2])

def pmi(word, freq, tot_w):
    pc = 1.0
    for ch in word:
        if ch not in char: return None
        pc *= char[ch] / tot_c
    return math.log2((freq / tot_w) / pc) / max(1, len(word) - 1)

# 过滤词表
FUNC = set('的了着过吗呢吧啊呀嘛哦么我你他她它们咱您就在也不没很都还又才被把给和与或这那些个来去说看想要做买用吃走叫让从对向里会能不')
LOC  = set('上下中时后前里外内间边处')
DEG  = set('太更最很非挺蛮极')
GLUE = ['自己','大家','我们','你们','他们','希望','建议','知道','发现','开始','比较','特别','非常',
        '如果','但是','因为','所以','而且','就是','不是','可以','没有','已经','正在','还是','或者',
        '以及','等等','什么','怎么','这样','那样','时候','一个','一些','一下','一定','一直']

def keep(w):
    if set(w) & FUNC: return False
    if len(w) >= 3 and w[-1] in LOC: return False
    if len(w) >= 3 and w[0] in DEG: return False
    if any(g in w for g in GLUE): return False
    return True

# 读外部词库 → 候选
cand = {}
for path in sys.argv[3:]:
    for ln in open(path, encoding='utf-8'):
        if ln.startswith('#') or '\t' not in ln: continue
        p = ln.rstrip('\n').split('\t')
        if len(p) < 2: continue
        w = p[0].strip()
        if len(w) < 2 or len(w) > 4 or w in local or not keep(w): continue
        f = int(p[2]) if len(p) > 2 and p[2].isdigit() else 0
        if cand.get(w, 0) < f: cand[w] = f

tot_w = sum(cand.values()) or 1
print('词,五笔码,词频,归一PMI')
for w, f in sorted(cand.items(), key=lambda x: -x[1]):
    c = word_code(w)
    pv = pmi(w, f, tot_w)
    if not c or pv is None or pv < 5.0:
        continue
    print(f'{w},{c},{f},{pv:.1f}')
