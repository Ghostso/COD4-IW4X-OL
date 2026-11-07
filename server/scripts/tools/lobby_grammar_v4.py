#!/usr/bin/env python3
"""Lobby 任务 payload 线格式 —— 最终文法 v4 (全部由真实字节反推)。

tag 语法 (每个都由 corpus 的 N 条样本实测确认, 证据见 papers/):

  0x00  terminator (可连续出现 1~2 次)
  0x01  bool            1B payload
  0x03  group           u8 count, 后接 count 个「元素」, 元素可为 tag 流或裸标量
  0x06  u16             2B payload              (10/20, 80/173, 80/203)
  0x07  u32             4B payload              (8/3 尾部 125 项, 21/1)
  0x08  u32             4B payload
  0x0a  u64             8B payload              (11/4 会话 id, 11/4 全 0)
  0x10  C-string        到 NUL, 可为空
  0x13  blob            '08' + u32 len + len B  (实测 1509 次, 0 例外)
  0x6c  u32 list        '08' + u32 N + N B + u32 M   (203/203 命中, M 恒 = N/4)
"""
import json
import struct
import sys
from collections import Counter, defaultdict

TERM = 0x00


class Buf:
    __slots__ = ("b", "i", "ok", "err")

    def __init__(self, b):
        self.b = b
        self.i = 0
        self.ok = True
        self.err = ""

    def fail(self, e):
        self.ok = False
        self.err = e
        return None

    def byte(self):
        if self.i >= len(self.b):
            return self.fail("eof@%d" % self.i)
        v = self.b[self.i]
        self.i += 1
        return v

    def u32(self):
        if self.i + 4 > len(self.b):
            return self.fail("u32 eof@%d" % self.i)
        v = struct.unpack_from("<I", self.b, self.i)[0]
        self.i += 4
        return v

    def raw(self, k):
        if self.i + k > len(self.b):
            return self.fail("raw%d eof@%d" % (k, self.i))
        v = self.b[self.i:self.i + k]
        self.i += k
        return v

    def cstr(self):
        z = self.b.find(b"\x00", self.i)
        if z < 0:
            return self.fail("cstr no nul @%d" % self.i)
        v = self.b[self.i:z]
        self.i = z + 1
        return v


def elem(buf, depth=0):
    """解析一个元素, 返回 (kind, value)。"""
    if depth > 3:
        return buf.fail("depth") or (None, None)
    t = buf.byte()
    if t is None:
        return (None, None)
    if t == 0x08:
        return ("u32", buf.u32())
    if t == 0x07:
        return ("u32", buf.u32())
    if t == 0x06:
        return ("u16", buf.raw(2))
    if t == 0x01:
        return ("bool", buf.raw(1))
    if t == 0x0A:
        return ("u64", buf.raw(8))
    if t == 0x10:
        return ("str", buf.cstr())
    if t == 0x13:
        sub = buf.byte()
        if sub != 0x08:
            return buf.fail("13sub=%02x" % sub) or (None, None)
        n = buf.u32()
        return ("blob", buf.raw(n))
    if t == 0x6C:
        sub = buf.byte()
        if sub != 0x08:
            return buf.fail("6csub=%02x" % sub) or (None, None)
        n = buf.u32()
        body = buf.raw(n)
        m = buf.u32()
        return ("list", (body, m))
    if t == 0x03:
        # 成组: count 后接元素。子元素可以带 tag, 也可以是裸标量(用首个字节判断)
        cnt = buf.byte()
        if cnt is None:
            return (None, None)
        if cnt > 16:
            return buf.fail("03cnt=%d" % cnt) or (None, None)
        items = []
        for _ in range(cnt):
            k, v = elem(buf, depth + 1)
            if not buf.ok:
                return (None, None)
            items.append((k, v))
        return ("group", items)
    return buf.fail("tag %02x @%d" % (t, buf.i - 1)) or (None, None)


def parse(b, strict_term=True):
    buf = Buf(b)
    out = []
    while buf.i < len(b):
        if b[buf.i] == TERM:
            while buf.i < len(b) and b[buf.i] == TERM:
                buf.i += 1
            if buf.i == len(b):
                return True, out, ""
            if strict_term:
                return False, out, "trail %dB @%d tag=%02x" % (
                    len(b) - buf.i, buf.i, b[buf.i])
            continue
        k, v = elem(buf)
        if not buf.ok:
            return False, out, buf.err
        out.append((k, v))
    return True, out, ""


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
                if len(fails) < 10:
                    fails.append((k, why, b[:48].hex()))
        ok_t += ok
        bad_t += bad
        if bad:
            print("%3d/%-3d ok=%-4d bad=%-4d <<<" % (k[0], k[1], ok, bad))
    print()
    print("TOTAL ok=%d bad=%d (%.2f%%)" % (ok_t, bad_t, 100.0 * ok_t / max(1, ok_t + bad_t)))
    for k, why, h in fails:
        print("  %3d/%-3d %-30s %s" % (k[0], k[1], why, h))


if __name__ == "__main__":
    main()
