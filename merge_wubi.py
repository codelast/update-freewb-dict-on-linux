#!/usr/bin/env python3
"""把 (词, 五笔码) 并入码表，type=0。用法: merge_wubi.py <源.mb> <候选.csv> <输出.mb>
CSV 至少含列：词,五笔码（其余列忽略）。已存在的词自动跳过。
"""
import sys, csv
import mb_table

src, cand_csv, dst = sys.argv[1], sys.argv[2], sys.argv[3]

t = mb_table.read(src)
have = {r[1].rstrip(b'\x00').decode('utf-8', 'ignore') for r in t.records}

items, dup = [], 0
for row in csv.DictReader(open(cand_csv, encoding='utf-8')):
    w = (row.get('词') or '').strip()
    c = (row.get('五笔码') or '').strip()
    if not w or not c:
        continue
    if w in have:
        dup += 1
        continue
    items.append((c.encode(), w.encode(), 0))       # 0 = 五笔

n = mb_table.insert_sorted(t, items)
mb_table.write(dst, t)
print(f'{src}: {len(t.records) - n:,} 条 → {len(t.records):,} 条（新增 {n}，已存在跳过 {dup}）')
