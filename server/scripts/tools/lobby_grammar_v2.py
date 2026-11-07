#!/usr/bin/env python3
"""Lobby 任务 payload 线格式: 经验推导的完整文法 (v2)。

从 corpus 的 6848 条真实客户端字节反推, 不引用任何外部项目。

tag 表 (全部由样本反推, 见每条的推导依据):
   0x08  u32le            (4B)   见 6/5: 08 14 00 00 00 = 20
   0x10  C-string                到 NUL, 可为空(紧跟 00)
   0x13  0x08 + u32le len + data 见 71/4: 13 08 10 00 00 00 + 16B
   0x0a  8B 定长 blob            见 11/4: 0a 88 77 66 55 44 33 22 11
   0x07  5B 定长 blob            见 21/5: 07 ab ad 92 d6 6b  (ab ad 92 d6 6b = 5B)
   0x01  1B bool
   0x00  终止符 (1~2 个)
"""
import json
import struct
import sys
from collections import Counter, defaultdict

# tag -> (kind, size)
FIXED = {
    0x08: 4,
    0x0a: 8,
    0x07: 5,
    0x01: 1,
}


def parse(p):
    off, ops = 0, []
    n = len(p)
    while off < n:
        start = off
        t = p[off]
        if t == 0x00:
            ops.append((start, t, b""))
            off += 1
            while off < n and p[off] == 0x00:
                ops.append((off, 0x00, b""))
                off += 1
            if off != n:
                return False, ops, "trailing %dB after term (next=%02x)" % (n - off, p[off])
            return True, ops, ""
        if t in FIXED:
            k = FIXED[t]
            if off + 1 + k > n:
                return False, ops, "%02x truncated need %d have %d" % (t, k, n - off - 1)
            ops.append((start, t, p[off + 1:off + 1 + k]))
            off += 1 + k
            continue
        if t == 0x10:
            z = p.find(b"\x00", off + 1)
            if z < 0:
                return False, ops, "10 no nul"
            ops.append((start, t, p[off + 1:z]))
            off = z + 1
            continue
        if t == 0x13:
            if off + 6 > n or p[off + 1] != 0x08:
                return False, ops, "13 sub=%02x" % (p[off + 1] if off + 1 < n else 0)
            ln = struct.unpack_from("<I", p, off + 2)[0]
            if off + 6 + ln > n:
                return False, ops, "13 len=%d overflow (have %d)" % (ln, n - off - 6)
            ops.append((start, t, p[off + 6:off + 6 + ln]))
            off += 6 + ln
            continue
        return False, ops, "unknown tag %02x" % t
    return True, ops, "eof-no-term"


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    show = "--show-unknown" in sys.argv
    per = defaultdict(list)
    for r in corpus:
        per[(r["svc"], r["task"])].append(bytes.fromhex(r["payload"]))

    ok_tot = bad_tot = 0
    tagc = Counter()
    badkinds = Counter()
    badsamples = defaultdict(list)
    for k in sorted(per):
        ok = bad = 0
        for p in per[k]:
            good, ops, why = parse(p)
            for _o, t, _v in ops:
                tagc[t] += 1
            if good:
                ok += 1
            else:
                bad += 1
                badkinds[why.split(" ")[0]] += 1
                if len(badsamples[why.split(" ")[0]]) < 4:
                    badsamples[why.split(" ")[0]].append((k, why, p[:48].hex()))
        ok_tot += ok
        bad_tot += bad
        flag = "" if bad == 0 else "   <<<"
        print("%3d/%-3d ok=%-4d bad=%-4d%s" % (k[0], k[1], ok, bad, flag))

    print()
    print("TOTAL ok=%d bad=%d (%.2f%%)" % (ok_tot, bad_tot,
          100.0 * ok_tot / max(1, ok_tot + bad_tot)))
    print("tags used:", " ".join("%02x:%d" % (t, c) for t, c in sorted(tagc.items())))
    print()
    print("failure classes:")
    for kind, c in badkinds.most_common():
        print("  %-28s %d" % (kind, c))
        for k, why, h in badsamples[kind]:
            print("      %3d/%-3d  %-24s %s" % (k[0], k[1], why, h))


if __name__ == "__main__":
    main()
