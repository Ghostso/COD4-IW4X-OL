#!/usr/bin/env python3
"""按假设文法解析 lobby 任务 payload, 统计每种 opcode 的形态与成功率。

假设文法 (待验证):
    op 0x08  : u32le 标量 (4 字节)
    op 0x13  : 08 | u32le len | len 字节
    op 0x10  : C 字符串 (到 NUL)
    op 0x0a  : 8 字节
    op 0x07  : 5 字节
    op 0x01  : 4 字节
    op 0x00  : 结束

输出: 每种 opcode 的成功/失败次数, 以及失败样本的头 32 字节。
"""
import json
import struct
import sys
from collections import Counter, defaultdict

SIZES = {0x0A: 8, 0x07: 5, 0x01: 4}


def parse(p):
    """返回 (ok, ops, reason)。ops = [(off, opcode, payload)]"""
    off, ops = 0, []
    n = len(p)
    while off < n:
        op = p[off]
        start = off
        if op == 0x00:
            ops.append((start, op, b""))
            off += 1
            # 允许一个尾随 0x00
            if off < n and p[off] == 0x00:
                off += 1
            if off != n:
                return False, ops, "trailing %d bytes after 00" % (n - off)
            return True, ops, ""
        if op == 0x08:
            if off + 5 > n:
                return False, ops, "08 truncated"
            ops.append((start, op, p[off + 1:off + 5]))
            off += 5
            continue
        if op == 0x13:
            if off + 6 > n or p[off + 1] != 0x08:
                return False, ops, "13 sub=%s" % (p[off + 1] if off + 1 < n else "eof")
            ln = struct.unpack_from("<I", p, off + 2)[0]
            if off + 6 + ln > n:
                return False, ops, "13 len=%d overflow" % ln
            ops.append((start, op, p[off + 6:off + 6 + ln]))
            off += 6 + ln
            continue
        if op == 0x10:
            z = p.find(b"\x00", off + 1)
            if z < 0:
                return False, ops, "10 no nul"
            ops.append((start, op, p[off + 1:z]))
            off = z + 1
            continue
        if op in SIZES:
            k = SIZES[op]
            if off + 1 + k > n:
                return False, ops, "%02x truncated" % op
            ops.append((start, op, p[off + 1:off + 1 + k]))
            off += 1 + k
            continue
        return False, ops, "unknown op %02x" % op
    return True, ops, "eof-no-term"


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    per = defaultdict(list)
    for r in corpus:
        per[(r["svc"], r["task"])].append(bytes.fromhex(r["payload"]))

    grand_ok = grand_bad = 0
    opcount = Counter()
    fails = defaultdict(list)
    for k in sorted(per):
        ok = bad = 0
        for p in per[k]:
            good, ops, why = parse(p)
            for _o, op, _pl in ops:
                opcount[op] += 1
            if good:
                ok += 1
            else:
                bad += 1
                if len(fails[k]) < 3:
                    fails[k].append((why, p[:40].hex()))
        grand_ok += ok
        grand_bad += bad
        print("%3d/%-3d ok=%-4d bad=%-4d" % (k[0], k[1], ok, bad))
        for why, h in fails[k]:
            print("        ! %-22s %s" % (why, h))

    print()
    print("TOTAL ok=%d bad=%d (%.1f%%)" % (grand_ok, grand_bad,
          100.0 * grand_ok / max(1, grand_ok + grand_bad)))
    print("opcodes:", " ".join("%02x:%d" % (o, c) for o, c in sorted(opcount.items())))


if __name__ == "__main__":
    main()
