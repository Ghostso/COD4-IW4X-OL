#!/usr/bin/env python3
"""验证 0x03 = 成组标签(tag + count + count 个 tag 流)。

已知成组形态 (来自样本观测):
  03 01 0a <u32 x1>                         102/7/1: 03 01 0a 00000000
  03 02 13 08 <u32 len> <data>  13 08 <u32len> <data>   68/3
  03 03 (0a <u32>) x3                       102/1
  03 01 03 02 00                            102/5
  03 <count> <...>                          其余

判据: 若 0x03 后面一字节是 n (<=8), 且其后能正好解析出 n 个「元素」, 且之后跟终止符/下一字段, 则成立。
"""
import json
import struct
import sys
from collections import defaultdict


class P:
    def __init__(self, b, i=0):
        self.b = b
        self.i = i
        self.ok = True

    def eof(self):
        return self.i >= len(self.b)

    def peek(self):
        return self.b[self.i] if self.i < len(self.b) else None

    def u32(self):
        if self.i + 4 > len(self.b):
            self.ok = False
            return None
        v = struct.unpack_from("<I", self.b, self.i)[0]
        self.i += 4
        return v

    def take(self, k):
        if self.i + k > len(self.b):
            self.ok = False
            return b""
        v = self.b[self.i:self.i + k]
        self.i += k
        return v


def read_str(p):
    z = p.b.find(b"\x00", p.i)
    if z < 0:
        p.ok = False
        return None
    s = p.b[p.i:z]
    p.i = z + 1
    return s


def read_bd(p, depth=0):
    """返回 (kind, value)。失败时 p.ok=False"""
    if depth > 4:
        p.ok = False
        return ("err", "depth")
    t = p.peek()
    if t is None:
        p.ok = False
        return ("err", "eof")
    if t == 0x08:
        p.i += 1
        return ("u32", p.u32())
    if t == 0x0a:
        p.i += 1
        return ("f64", p.take(8))
    if t == 0x07:
        p.i += 1
        return ("b5", p.take(5))
    if t == 0x01:
        p.i += 1
        return ("bool", p.take(1))
    if t == 0x10:
        p.i += 1
        return ("str", read_str(p))
    if t == 0x13:
        p.i += 1
        if p.peek() != 0x08:
            p.ok = False
            return ("err", "13 no 08")
        p.i += 1
        ln = p.u32()
        if ln is None:
            return ("err", "13 len")
        return ("blob", p.take(ln))
    if t == 0x6C:
        p.i += 1
        sub = p.peek()
        if sub == 0x7A:  # 追加变长计数
            p.take(2)
            n = p.u32()
        else:
            n = p.u32()
        if n is None or n > 1 << 16:
            p.ok = False
            return ("err", "list len")
        return ("list", n)
    if t == 0x03:
        p.i += 1
        n = p.b[p.i] if p.i < len(p.b) else None
        p.i += 1
        if n is None or n > 8:
            p.ok = False
            return ("err", "group count %r" % n)
        items = []
        for _ in range(n):
            k, v = read_bd(p, depth + 1)
            if not p.ok:
                return ("err", "group item")
            items.append((k, v))
        return ("group", items)
    p.ok = False
    return ("err", "tag %02x" % t)


def parse_all(b):
    p = P(b)
    out = []
    while not p.eof():
        if p.peek() == 0x00:
            # 终止
            while not p.eof() and p.peek() == 0x00:
                p.i += 1
            return (True, out) if p.eof() else (False, out)
        k, v = read_bd(p)
        if not p.ok:
            return False, out
        out.append((k, v))
    return True, out


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    per = defaultdict(list)
    for r in corpus:
        per[(r["svc"], r["task"])].append(bytes.fromhex(r["payload"]))
    ok_t = bad_t = 0
    fails = []
    for k in sorted(per):
        ok = bad = 0
        for b in per[k]:
            good, _ = parse_all(b)
            if good:
                ok += 1
            else:
                bad += 1
                if len(fails) < 8:
                    fails.append((k, b[:40].hex()))
        ok_t += ok
        bad_t += bad
        if bad:
            print("%3d/%-3d ok=%-4d bad=%-4d <<<" % (k[0], k[1], ok, bad))
    print()
    print("TOTAL ok=%d bad=%d (%.2f%%)" % (ok_t, bad_t, 100.0 * ok_t / max(1, ok_t + bad_t)))
    for k, h in fails:
        print("  fail %3d/%-3d %s" % (k[0], k[1], h))


if __name__ == "__main__":
    main()
