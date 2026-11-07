#!/usr/bin/env python3
"""对已解 tag 做语义分析: 收集每个 tag 的载荷, 判断是整型/浮点/字符串。

输出每个 tag 的:
  - 样本数、不同值个数
  - u32 解释是否"像整数" (多数值 < 2^20 且高位为 0)
  - 若为 8 字节: 比较 u64 / f64 / (u32,u32) 三种解释的可信度
"""
import json
import struct
import sys
from collections import Counter, defaultdict


def read_str(b, i):
    z = b.find(b"\x00", i)
    if z < 0:
        return None, i
    return b[i:z], z + 1


def walk(b):
    """宽松遍历, 返回 [(off, tag, payload)]"""
    i, out = 0, []
    n = len(b)
    while i < n:
        t = b[i]
        if t == 0x00:
            i += 1
            continue
        if t == 0x08:
            out.append((i, t, b[i + 1:i + 5]))
            i += 5
        elif t == 0x07:
            out.append((i, t, b[i + 1:i + 5]))
            i += 5
        elif t == 0x0a:
            out.append((i, t, b[i + 1:i + 9]))
            i += 9
        elif t == 0x01:
            out.append((i, t, b[i + 1:i + 2]))
            i += 2
        elif t == 0x10:
            s, i2 = read_str(b, i + 1)
            if s is None:
                return out, False
            out.append((i, t, s))
            i = i2
        elif t == 0x13:
            if i + 5 >= n:
                return out, False
            ln = struct.unpack_from("<I", b, i + 2)[0]
            out.append((i, t, b[i + 6:i + 6 + ln]))
            i += 6 + ln
        elif t == 0x6C:
            sub = b[i + 1]
            k = 5 if sub == 0x7A else 1
            cnt = struct.unpack_from("<I", b, i + k)[0]
            if cnt > 4096:
                return out, False
            out.append((i, t, b[i + k + 4:i + k + 4 + cnt * 4]))
            i += k + 4 + cnt * 4
        elif t == 0x03:
            # 未知结构, 停下
            return out, False
        else:
            return out, False
    return out, True


def main():
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    stats = defaultdict(list)
    for r in corpus:
        b = bytes.fromhex(r["payload"])
        ops, _ok = walk(b)
        for _o, t, pl in ops:
            stats[t].append(pl)

    for t in sorted(stats):
        v = stats[t]
        print("=== tag %02x  n=%d distinct=%d" % (t, len(v), len(set(v))))
        head = [x for x in v[:400]]
        if t == 0x10:
            ss = [x.decode("latin1", "replace") for x in v[:8]]
            print("  strings:", ss)
            asc = sum(1 for x in v if all(32 <= c < 127 for c in x))
            print("  可打印占比: %d/%d" % (asc, len(v)))
        elif t in (0x08, 0x07):
            ints = [struct.unpack("<i", x)[0] for x in v]
            un = [struct.unpack("<I", x)[0] for x in v]
            small = sum(1 for u in un if u < 1 << 20)
            neg = sum(1 for s in ints if s < 0)
            print("  u32<2^20 占比 %d/%d  负(signed) %d  值域 [%d, %d]" % (
                small, len(v), neg, min(ints), max(ints)))
            print("  最常见:", [("%d" % s) for s, _ in Counter(ints).most_common(8)])
        elif t == 0x0a:
            u64 = [struct.unpack("<Q", x)[0] for x in v if len(x) == 8]
            f64 = [struct.unpack("<d", x)[0] for x in v if len(x) == 8]
            lo = [struct.unpack("<I", x[:4])[0] for x in v if len(x) == 8]
            hi = [struct.unpack("<I", x[4:])[0] for x in v if len(x) == 8]
            sanef = sum(1 for f in f64 if f == f and abs(f) < 1e12 and (f == 0 or abs(f) > 1e-9))
            print("  作为 u64 : 范围 [%d, %d]" % (min(u64), max(u64)))
            print("  作为 f64 : 合理值 %d/%d  样本 %s" % (sanef, len(f64), f64[:4]))
            print("  拆两 u32 : lo 常见 %s" % Counter(lo).most_common(4))
            print("            hi 常见 %s" % Counter(hi).most_common(4))
            print("  作为 f64 常见:", Counter(f64).most_common(5))
        elif t == 0x13:
            ln = [len(x) for x in v]
            print("  blob 长度分布:", Counter(ln).most_common(10))
            print("  样本:", v[0][:32].hex() if v else "")
        elif t == 0x6C:
            ln = [len(x) // 4 for x in v]
            print("  元素数分布:", Counter(ln).most_common(10))
        elif t == 0x01:
            print("  值分布:", Counter(x.hex() for x in v).most_common(6))


if __name__ == "__main__":
    main()
