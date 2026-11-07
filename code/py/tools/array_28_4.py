#!/usr/bin/env python3
"""28/4 精确解析：0x6c 数组的 body/cnt 与 u32 序列。"""
import json
import struct
import sys

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

corpus = json.load(open(sys.argv[1], encoding="utf-8"))
for r in corpus:
    if (r["svc"], r["task"]) != (28, 4):
        continue
    b = bytes.fromhex(r["payload"])
    good, els, why = G.parse(b)
    cnt, body = els[0][1]
    print("len=%d  good=%s" % (len(b), good))
    print("0x6c: bytelen=%d  cnt(尾部u32)=%d  body 长度=%d" % (len(body), cnt, len(body)))
    us = [struct.unpack("<I", body[i:i + 4])[0] for i in range(0, len(body), 4)]
    print("body 内 u32 个数 = %d" % len(us))
    print("前 8 个: %s" % us[:8])
    print("后 8 个: %s" % us[-8:])
    print("是否严格递增: %s" % all(us[i] < us[i + 1] for i in range(len(us) - 1)))
    print("首值=%d  末值=%d  cnt=%d" % (us[0], us[-1], cnt))
    print("us[1:] 是否 = 0..? 递增序列, 缺号:", sorted(set(range(us[1], us[-1] + 1)) - set(us[1:]))[:30])
    # 检查是否存在 u32==255
    print("u32 == 255 的位置:", [i for i, x in enumerate(us) if x == 255])
    print("该位置在原始字节中的偏移:", 6 + 4 * [i for i, x in enumerate(us) if x == 255][0])
    break
