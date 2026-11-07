#!/usr/bin/env python3
"""Lobby 任务 payload 线格式 —— 文法 v5。

修正 v4 的错误: 0x03 不是"组", 而是 u8 (1 字节值)。
证据:
  102/1  08 00.. 08 01.. | 03 03 | 0a <u64> | 00         = 5+5+2+9+1 = 22 ✓
  102/1  08 00.. 08 02.. | 03 01 | 0a <u64> | 03 02 | 0a <u64> | 00 = 33 ✓
  102/5  08 02.. | 03 01 | 03 02 | 00                    = 5+2+2+1 = 10 ✓
  102/7  08 32.. | [03 01 | 0a <u64>] x50 | 00           = 5+550+1 = 556 ✓
  68/3   10 "" | 0a <8B> | 10 "" | 03 01 | 13 08 <22B> | 00 ✓

tag 表:
  00 term   01 bool(1B)   03 u8(1B)   06 u16(2B)   07 i32(4B)
  08 u32(4B)  09 i64(8B)  0a u64(8B)  10 cstr
  13 blob = 13 08 <u32 len> <len B>
  6c array = 6c 08 <u32 bytelen> <u32 count> <bytelen B>
"""
import json
import struct
import sys
from collections import defaultdict

FIXED = {0x01: 1, 0x03: 1, 0x06: 2, 0x07: 4, 0x08: 4, 0x09: 8, 0x0A: 8}


class Buf:
    __slots__ = ("b", "i", "ok", "err")

    def __init__(self, b):
        self.b, self.i, self.ok, self.err = b, 0, True, ""

    def fail(self, e):
        self.ok = False
        self.err = e
        return None

    def take(self, k, what):
        if self.i + k > len(self.b):
            return self.fail("%s eof@%d need %d" % (what, self.i, k))
        v = self.b[self.i:self.i + k]
        self.i += k
        return v

    def u32(self, what="u32"):
        v = self.take(4, what)
        return None if v is None else struct.unpack("<I", v)[0]


def elem(buf, depth=0):
    if depth > 2:
        return buf.fail("depth")
    t = buf.take(1, "tag")
    if t is None:
        return None
    t = t[0]
    if t in FIXED:
        return (t, buf.take(FIXED[t], "tag%02x" % t))
    if t == 0x10:
        z = buf.b.find(b"\x00", buf.i)
        if z < 0:
            return buf.fail("cstr@%d" % buf.i)
        v = buf.b[buf.i:z]
        buf.i = z + 1
        return (t, v)
    if t == 0x13:
        if buf.take(1, "13sub") != b"\x08":
            return buf.fail("13sub")
        n = buf.u32("13len")
        if n is None:
            return None
        return (t, buf.take(n, "13body"))
    if t == 0x6C:
        if buf.take(1, "6csub") != b"\x08":
            return buf.fail("6csub")
        bl = buf.u32("6clen")
        if bl is None:
            return None
        body = buf.take(bl, "6cbody")
        cnt = buf.u32("6ccnt")
        if body is None or cnt is None:
            return None
        return (t, (cnt, body))
    if t == 0x6B:
        # 与 0x6c 同构: 6b 08 <u32 byteLen> <byteLen B> <u32 count>
        if buf.take(1, "6bsub") != b"\x08":
            return buf.fail("6bsub")
        bl = buf.u32("6blen")
        if bl is None:
            return None
        body = buf.take(bl, "6bbody")
        cnt = buf.u32("6bcnt")
        if body is None or cnt is None:
            return None
        return (t, (cnt, body))
    return buf.fail("tag %02x @%d" % (t, buf.i - 1))


def parse(b):
    buf = Buf(b)
    out = []
    while buf.i < len(b):
        if b[buf.i] == 0x00:
            while buf.i < len(b) and b[buf.i] == 0x00:
                buf.i += 1
            if buf.i < len(b):
                return False, out, "trail %dB tag %02x" % (
                    len(b) - buf.i, b[buf.i])
            return True, out, ""
        e = elem(buf)
        if not buf.ok:
            return False, out, buf.err
        out.append(e)
    return True, out, "eof"


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
            good, _o, why = parse(b)
            if good:
                ok += 1
            else:
                bad += 1
                if len(fails) < 12:
                    fails.append((k, why, b[:56].hex()))
        ok_t += ok
        bad_t += bad
        if bad:
            print("%3d/%-3d ok=%-4d bad=%-4d <<<" % (k[0], k[1], ok, bad))
    print()
    print("TOTAL ok=%d bad=%d (%.2f%%)" % (ok_t, bad_t,
          100.0 * ok_t / max(1, ok_t + bad_t)))
    for k, why, h in fails:
        print("  %3d/%-3d %-26s %s" % (k[0], k[1], why, h))


if __name__ == "__main__":
    main()
