#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""s137 · B14: 8/3 blob (zlib 解压 32768B) 逐段结构闭合 (纯静态).

输入: corpus.json (字段 svc/task/payload(hex))
输出: 逐字节列不变量 / 可变区记录结构 / 标志位与ID区 / 28/4 对照 / 未闭合项

用法:
  python -I tools/s137_8_3_32kb_invariants.py <corpus.json> <out.txt>
"""
import collections
import json
import math
import struct
import sys
import zlib

sys.path.insert(0, "tools")
import lobby_grammar_v5 as G  # noqa: E402

SIGS = [b"\x78\x01", b"\x78\x9c", b"\x78\xda", b"\x78\x5e"]
N = 32768


# ------------------------------------------------------------------ 取样本
def load(corpus):
    recs = [r for r in corpus if r["svc"] == 8 and r["task"] == 3]
    out, notes = [], collections.Counter()
    for r in recs:
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            notes["parse_fail"] += 1
            continue
        blob = [v for t, v in els if t == 0x13]
        if len(blob) != 1:
            notes["no_blob"] += 1
            continue
        d = blob[0]
        st = next((i for s in SIGS for i in [d.find(s)] if i >= 0), -1)
        if st < 0:
            notes["no_sig"] += 1
            continue
        try:
            dec = zlib.decompress(d[st:])
        except Exception:
            notes["zlib_fail"] += 1
            continue
        notes["declen_%d" % len(dec)] += 1
        if len(dec) == N:
            out.append(dec)
    return out, notes


def ranges(offs):
    if not offs:
        return []
    out, s, p = [], offs[0], offs[0]
    for x in offs[1:]:
        if x == p + 1:
            p = x
            continue
        out.append((s, p + 1))
        s = p = x
    out.append((s, p + 1))
    return out


def entropy(c, n):
    h = 0.0
    for v in c.values():
        p = v / n
        h -= p * math.log2(p)
    return h


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    corpus = json.load(open(sys.argv[1], encoding="utf-8"))
    out = open(sys.argv[2], "w", encoding="utf-8")

    def P(*a):
        s = " ".join(str(x) for x in a)
        print(s)
        out.write(s + "\n")

    S, notes = load(corpus)
    n = len(S)
    P("=== B14 · 8/3 (32768B 解压体) 逐段闭合 · 样本 %d 条 ===" % n)
    P("解压备注:", dict(notes))
    d = S[0]

    # ---------- (1) 逐字节列不变量 ----------
    nv, top = [], []
    for i in range(N):
        c = collections.Counter(s[i] for s in S)
        nv.append(len(c))
        top.append(c)
    const = [i for i in range(N) if nv[i] == 1]
    low = [i for i in range(N) if 2 <= nv[i] <= 6]
    high = [i for i in range(N) if nv[i] > 6]

    P("\n## 1 逐字节列不变量 (84 样本 × 32768)")
    P("恒定字节 = %d (%.3f%%)   低熵(2..6取值) = %d (%.1f%%)   高熵(>6取值) = %d (%.1f%%)"
      % (len(const), 100.0 * len(const) / N, len(low), 100.0 * len(low) / N,
         len(high), 100.0 * len(high) / N))

    cr = ranges(const)
    big = [(a, b) for a, b in cr if b - a >= 16]
    P("恒定区间数 = %d (其中 >=16B 的有 %d 个)" % (len(cr), len(big)))
    P("  >=16B 的恒定区间:")
    for a, b in big:
        v = d[a:b]
        P("    [%5d,%5d) len=%5d val=%s" % (a, b, b - a,
          v.hex()[:24] + (".." if len(v) > 12 else "")))

    P("\n  低熵区间 (2..6 取值):")
    for a, b in ranges(low):
        vals = collections.Counter()
        for i in range(a, b):
            vals.update(top[i])
        distinct = sorted(set(
            k for i in range(a, b) for k in top[i]))
        P("    [%5d,%5d) len=%d 取值集=%s" % (
            a, b, b - a, [("%02x" % k) for k in distinct][:10]))

    P("\n  高熵区间 (>6 取值):")
    for a, b in ranges(high):
        hm = max(entropy(top[i], n) for i in range(a, b))
        h0 = min(entropy(top[i], n) for i in range(a, b))
        P("    [%5d,%5d) len=%5d 熵[%.1f..%.1f]" % (a, b, b - a, h0, hm))

    # ---------- (1b) 段地图 ----------
    def cls(v):
        if v == 0:
            return "Z"
        if v == 1:
            return "1"
        if v <= 0x100:
            return "s"
        if 0x2700 <= v <= 0x27ff:
            return "A"
        if 0xea00 <= v <= 0xeaff:
            return "B"
        if v > 0xffff:
            return "X"
        return "o"

    P("\n## 1b 段地图 (基址 3862, 每 64B 块的字种类构成; 字=u32@3862+4k)")
    P("   种类: Z=0 1=值1 s=小(<=0x100) A=0x27xx(~1e4) B=0xeaXX(~6e4) X=>0xffff o=其它")
    for a in range(3862, 15756, 64):
        ks = collections.Counter()
        for i in range(a, min(a + 64, 15756) - 3, 4):
            ks[cls(struct.unpack_from("<I", d, i)[0])] += 1
        keys = "".join(k for k, _ in ks.most_common())
        P("    [%5d,%5d)  %s" % (a, min(a + 64, 15756), keys))

    # ---------- (2) 可变区结构 ----------
    P("\n## 2 可变区记录结构")
    var = [i for i in range(N) if nv[i] > 1]
    P("可变字节 ... 首可变=%d 末可变=%d" % (var[0], var[-1]))
    P("[12,3862) 是否全恒定 = %s" % all(i in set(const) for i in range(12, 3862)))
    P("[15756,32768) 是否全恒定 = %s  (尾部=%d B)"
      % (all(i in set(const) for i in range(15756, N)), N - 15756))
    tailvar = [i for i in var if i >= 3862]
    P("尾段可变字节 mod 4 分布 = %s  ⇒ 无固定4字节栅格"
      % dict(sorted(collections.Counter(i % 4 for i in tailvar).items())))

    # 周期检验 (聚合 84 样本, 任一不同即失配)
    def period(A, B, maxp=380):
        res = []
        for p in range(1, maxp):
            bad = 0
            for i in range(A, B - p):
                for s in S:
                    if s[i] != s[i + p]:
                        bad += 1
                        break
            res.append((bad, p))
        res.sort()
        return res[:6]

    for (A, B) in [(4362, 8498), (9886, 13122), (13322, 14422)]:
        r = period(A, B)
        P("  周期检验[%d,%d): best=%s" % (A, B, [(p, b) for b, p in r]))
    P("  ⇒ 最佳周期仍有 ~7% 字节失配 ⇒ 非严格周期模板")

    # u16 细胞模型: 偶数偏移上非零 u16
    even_nz = collections.Counter()
    for s in S:
        for i in range(3862, N - 1, 2):
            if struct.unpack_from("<H", s, i)[0]:
                even_nz[i] += 1
    gaps = collections.Counter(sorted(even_nz)[k + 1] - sorted(even_nz)[k]
                               for k in range(len(even_nz) - 1))
    P("  偶数偏移上曾非零的 u16 位置数 = %d" % len(even_nz))
    P("  其相邻间隔分布 top8 = %s  ⇒ 主体间距4(2字节值+2字节0填充)"
      % gaps.most_common(8))

    # ---------- (3) 标志位/ID 区 ----------
    P("\n## 3 标志位 / ID 区")
    for base in (0, 2):
        vals = collections.Counter()
        for s in S:
            for i in range(base, N - 3, 4):
                v = struct.unpack_from("<I", s, i)[0]
                if v:
                    vals[v] += 1
        if not vals:
            continue
        tot = sum(vals.values())
        pow2 = sum(c for v, c in vals.items() if v & (v - 1) == 0)
        one = vals.get(1, 0)
        P("  u32 基址 mod4==%d : 非零值种数=%d 总计数=%d  值=1:%d(%.0f%%)  2的幂:%.0f%%"
          % (base, len(vals), tot, one, 100.0 * one / tot, 100.0 * pow2 / tot))
        P("     top20: %s" % [(("%08x" % v), c) for v, c in vals.most_common(20)])

    # ID 值位置分布
    for label, lo, hi in [("0x27xx(~10000)", 0x2700, 0x27ff),
                          ("0xeaXX(~60000)", 0xea00, 0xeaff)]:
        pos = collections.Counter()
        for s in S:
            for i in range(0, N - 3, 2):
                v = struct.unpack_from("<H", s, i)[0]
                if lo <= v <= hi:
                    pos[i] += 1
        P("  %s : 出现位置数=%d 首10=%s" % (label, len(pos), sorted(pos)[:10]))

    # ---------- (3b) 28/4 对照 ----------
    P("\n## 3b 28/4 ContentUnlock2 对照")
    r28 = [r for r in corpus if r["svc"] == 28 and r["task"] == 4]
    slots, tailcnt = None, None
    for r in r28:
        b = bytes.fromhex(r["payload"])
        good, els, why = G.parse(b)
        if not good:
            continue
        arrs = [v for t, v in els if t in (0x6C, 0x6B)]
        if not arrs:
            continue
        cnt, body = arrs[0]
        tailcnt = cnt
        m = len(body) // 4
        slots = list(struct.unpack_from("<%dI" % m, body, 0))
        break
    if slots:
        P("  28/4 样本 %d 条; 体首u32=%d (=byteLen/4) 元素=%d 个; 尾部count=%d"
          % (len(r28), slots[0], len(slots) - 1, tailcnt))
        P("  槽ID(去掉首u32): min=%d max=%d" % (min(slots[1:]), max(slots[1:])))
        P("  前24槽: %s" % slots[1:25])
        slotid = set(slots[1:])
        P("  唯一槽ID数=%d; 槽域 0..%d" % (len(slotid), max(slots[1:])))
        # 8/3 里是否有落在槽域的值 (小值)
        small = collections.Counter()
        for s in S:
            for i in range(0, N - 3, 2):
                v = struct.unpack_from("<H", s, i)[0]
                if v <= 262:
                    small[v] += 1
        P("  8/3 内 u16<=262 的取值种数=%d (含0/1)" % len(small))
        P("    非0/1 的小值: %s" % sorted(v for v in small if v > 1)[:40])
        inter = (set(small) & slotid)
        P("  8/3 小值 ∩ 28/4槽ID = %d 个 : %s" % (len(inter), sorted(inter)[:40]))

    # ---------- (4) 未闭合 ----------
    P("\n## 4 未闭合部分 (诚实清单)")
    P("  a) 可变区不是固定步长记录数组: 可变字节 mod4 近似均匀(273/278/281/290),")
    P("     最好字节周期 114 仍失配 275/4022 ⇒ 无严格重复模板; 无法给出")
    P("     '步长×条数×字段偏移' 的唯一定式。仅可言: 值以 u16 细胞(2B值+2B 0填充)")
    P("     反复出现, 与卷125 '每格2字节' 一致; 块1[4362,8498) 锚点(0x2711)间距恰114。")
    P("  b) 记录条数只能估: [4362,8498)≈36 个, [9886,13122)≈24 个; 与卷125 '1160段' 不对齐")
    P("     (1160 疑指细胞数或另一层计数, 未证实)。")
    P("  c) 0xea61(60001)/0xea8c(60044)/0x272c(10028)/0x2711(10001)/0x6467/0x61cb/0x567e")
    P("     等 ID 的语义未定 (既非 28/4 槽域 0..262 的成员, 也非已知识别串)。")
    P("  d) [0,4) 的 4B 哈希 (=payload u32#4) 与 [15000,15002) 2B 的含义未定。")
    P("  e) 与 'SKU 大整数' 的对应未建立 (证据不足)。")

    out.close()


if __name__ == "__main__":
    main()
