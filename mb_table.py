#!/usr/bin/env python3
"""fcitx4 码表 .mb 读写。格式依据 fcitx4 源码 src/im/table/tabledict.c。"""
import struct

class Table:
    def __init__(self, header, code_width, records):
        self.header = header        # 头部原始字节（含组词规则表），不含 recordCount
        self.W = code_width         # 码字段宽度 = pyCodeLen + 1
        self.records = records      # [[code:bytes, word:bytes含NUL, type:int, iHit:int, iIndex:int], ...]


def read(path):
    d = open(path, 'rb').read()
    assert struct.unpack_from('<I', d, 0)[0] == 0, 'not new-format table'
    version = d[4]
    p = 5
    keylen = struct.unpack_from('<I', d, p)[0]; p += 4
    p += keylen + 1                                   # KeyCode + NUL
    code_len, py_len = d[p], d[p + 1]; p += 2
    ignore = struct.unpack_from('<I', d, p)[0]; p += 4
    p += ignore + 1                                   # InvalidChar + NUL
    has_rule = d[p]; p += 1
    if has_rule:
        p += (code_len - 1) * (2 + code_len * 3)       # 组词规则表
    header = d[:p]
    count = struct.unpack_from('<I', d, p)[0]; p += 4
    W = py_len + 1
    recs = []
    while p < len(d):
        code = d[p:p + W].split(b'\x00')[0]
        q = p + W
        wl = struct.unpack_from('<I', d, q)[0]; q += 4
        word = d[q:q + wl]; q += wl                    # 含结尾 NUL
        typ = d[q]; q += 1
        hit, idx = struct.unpack_from('<II', d, q); q += 8
        recs.append([code, word, typ, hit, idx])
        p = q
    assert len(recs) == count, f'record count mismatch: {len(recs)} != {count}'
    return Table(header, W, recs)


def write(path, table):
    with open(path, 'wb') as f:
        f.write(table.header)
        f.write(struct.pack('<I', len(table.records)))
        for code, word, typ, hit, idx in table.records:
            f.write(code + b'\x00' * (table.W - len(code))   # 码字段左对齐、NUL 填充
                    + struct.pack('<I', len(word))            # 词长含结尾 NUL
                    + word
                    + bytes([typ])
                    + struct.pack('<II', hit, idx))


def insert_sorted(table, new_items):
    """把新记录按码插入；同码插在原组的**末尾**（候选里排最后）。
    new_items: [(code:bytes, word:bytes不含NUL, type:int)]
    """
    max_idx = max((r[4] for r in table.records), default=0)
    add = []
    for code, word, typ in new_items:
        max_idx += 1
        add.append([code, word + b'\x00', typ, 0, max_idx])
    add.sort(key=lambda r: (r[0], r[1]))

    out, i, ai = [], 0, 0
    recs = table.records
    while i < len(recs):
        if ai < len(add) and add[ai][0] < recs[i][0]:
            out.append(add[ai]); ai += 1
        else:
            cur = recs[i]; out.append(cur); i += 1
            # 已到该码组末尾 → 插新词
            if ai < len(add) and add[ai][0] == cur[0]:
                out.append(add[ai]); ai += 1
    out.extend(add[ai:])
    table.records = out
    return len(add)
