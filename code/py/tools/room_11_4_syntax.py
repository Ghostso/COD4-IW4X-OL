#!/usr/bin/env python3
"""验证 11/4 内层语法假设：

  body := u32 content_len | 02 | u8 groups | 00 00 | group*
  group := 0x00 | u8 id | 00 | 00 | u32 value     (5 字节粒度?)

观察：
  hdr=02 02 : 之后 00 08 00 00 | 00 80 08 00   <- 两组
  hdr=02 04 : 之后 00 30 00 00 | 00 e0 68 ab 5b ab 63 ab 03 00 00 00 00 98 03 00 00 10 10 00 00 00 20 0d 00 00 c0 c0 ...
  hdr=02 06 : 00 30 00 00 | 00 e0 68 ab 5b ab 63 ab 03 00 00 00 00 50 00 00 00 70 31 00 00 00 00 00 00 00 30 01 00 00 80 22 00 00 00 00 20 00 00 00 c0 a1 85 69 4d 31 15 f9 1c 00

假设：每组以 0x00 开头，后 1 字节是 id，再 2 字节 00 00，然后变长值。
先做纯统计：统计 "00 XX 00 00" 模式的出现。
"""
import json
import sys
from collections import Counter

sys.path.insert(0, "tools")
from lobby_grammar_v5 import parse


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    rs = [r for r in corpus if (r["svc"], r["task"]) == (11, 4)]
    forms = Counter()
    for r in rs:
        p = bytes.fromhex(r["payload"])
        ok, elems, _ = parse(p)
        if not ok:
            continue
        for k, v in elems:
            if k == 0x13:
                forms[v] += 1
                break

    # 对每个 blob，找所有 00 XX 00 00 模式
    ids = Counter()
    for b, n in forms.items():
        for i in range(4, len(b) - 3):
            if b[i] == 0 and b[i + 2] == 0 and b[i + 3] == 0:
                ids[b[i + 1]] += n
    print("所有 '00 XX 00 00' 模式里的 XX 分布（按出现次数加权）：")
    for k, v in ids.most_common(24):
        print("   XX=%02x  %d" % (k, v))
    print()

    # 检查 hdr=02 04 那个样本的切分
    b = None
    for bb, n in forms.items():
        if len(bb) >= 8 and bb[4] == 2 and bb[5] == 4:
            b = bb
            break
    print("样本 hdr=02 04: %s" % b.hex(" "))
    print("\n按 '00 XX 00 00' 切分：")
    i = 8
    while i < len(b) - 3:
        if b[i] == 0 and b[i + 2] == 0 and b[i + 3] == 0:
            print("  @%+4d id=%02x  next4=%s" % (i, b[i + 1], b[i + 4:i + 12].hex(" ")))
            i += 4
        else:
            i += 1


if __name__ == "__main__":
    main()
