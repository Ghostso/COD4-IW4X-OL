#!/usr/bin/env python3
"""单条记录全文十六进制+ASCII 转储, 用于逐字节读文法。"""
import json
import sys


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    want = sys.argv[2]
    idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    rs = [r for r in corpus if "%d/%d" % (r["svc"], r["task"]) == want]
    rs.sort(key=lambda r: r["len"])
    r = rs[min(idx, len(rs) - 1)]
    p = bytes.fromhex(r["payload"])
    print("svc/task=%s len=%d run=%s n=%d" % (want, len(p), r["run"], len(rs)))
    for off in range(0, len(p), 16):
        chunk = p[off:off + 16]
        hexs = " ".join("%02x" % c for c in chunk)
        asc = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        print("%04x  %-47s  %s" % (off, hexs, asc))
    print("TAIL_LAST8:", " ".join("%02x" % c for c in p[-8:]))


if __name__ == "__main__":
    main()
