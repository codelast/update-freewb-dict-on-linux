#!/usr/bin/env python3
"""把 (词, 拼音码) 作为 type=1 记录并入码表。
用法: merge_pinyin.py <源.mb> <拼音csv> <输出.mb> [跳过的码,逗号分隔]

注意：若某拼音码恰好等于一个**只有唯一候选**的五笔码，插入后会破坏"唯一即上屏"，
      这类码应放到跳过列表里。
"""
import sys, csv
import mb_table

src, py_csv, dst = sys.argv[1], sys.argv[2], sys.argv[3]
skip = set((sys.argv[4] if len(sys.argv) > 4 else '').split(','))

t = mb_table.read(src)
existing = {(r[1].rstrip(b'\x00'), r[0]) for r in t.records if r[2] == 1}
items = []
for row in csv.DictReader(open(py_csv, encoding='utf-8')):
    w = (row.get('词') or '').strip()
    c = (row.get('拼音码') or '').strip()
    if not w or not c or c in skip:
        continue
    if (w.encode(), c.encode()) in existing:
        continue
    items.append((c.encode(), w.encode(), 1))        # 1 = 拼音

n = mb_table.insert_sorted(t, items)
mb_table.write(dst, t)
print(f'{src}: {len(t.records) - n:,} 条 → {len(t.records):,} 条（新增拼音 {n}）')
