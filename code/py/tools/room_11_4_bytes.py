#!/usr/bin/env python3
"""11/4 内层按字节序列观察：这些"数值"看起来像位图或打包字段。
打印每种 hdr 的完整 hex，并检测 0x00 的位置节奏。"""
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

    for hdrm in (2, 4, 6, 8):
        cand = [(b, n) for b, n in forms.items()
                if len(b) >= 8 and b[4] == 2 and b[5] == hdrm]
        if not cand:
            continue
        cand.sort(key=lambda x: -x[1])
        b, n = cand[0]
        print("=" * 74)
        print("hdr=02 %02x 00 00   blob_len=%d  x%d" % (hdrm, len(b), n))
        print("  full hex:")
        for o in range(0, len(b), 16):
            seg = b[o:o + 16]
            asc = "".join(chr(c) if 32 <= c < 127 else "." for c in seg)
            print("   %+04d  %-47s  %s" % (o, seg.hex(" "), asc))
        # 找连续非零段的边界
        nz = [i for i, c in enumerate(b) if c]
        print("  非零区间: [%s .. %s]  共 %d 个非零字节" % (
            nz[0] if nz else "-", nz[-1] if nz else "-", len(nz)))
        print()


if __name__ == "__main__":
    main()
