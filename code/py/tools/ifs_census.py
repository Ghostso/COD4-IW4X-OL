#!/usr/bin/env python3
"""普查全部 .ifs：头部魔数、版本、清单、IWff 位置、载荷熵估算。

不读全文件（23GB），只读头 4KB + 尾 tail_len + 少量采样。
"""
import math
import os
import struct
import sys
from collections import Counter, defaultdict


def entropy(buf):
    if not buf:
        return 0.0
    c = Counter(buf)
    n = len(buf)
    e = 0.0
    for v in c.values():
        p = v / n
        e -= p * math.log(p, 2)
    return e


def parse_head(b):
    if len(b) < 0xAC or b[:4] != b"nifs":
        return {"magic": b[:4].hex(), "ok": False}
    d = {"ok": True}
    d["hdr_len"] = struct.unpack_from("<I", b, 4)[0]
    d["u16_0a"] = struct.unpack_from("<H", b, 0x0A)[0]
    d["tbl"] = [struct.unpack_from("<Q", b, 0x0C + i * 8)[0] for i in range(8)]
    d["tail_len"] = struct.unpack_from("<Q", b, 0x4C)[0]
    # 清单：0xac 起；名字之间用 00 分隔（实测 2 个 00）
    raw = b[0xAC:0xAC + 512]
    parts = []
    cur = bytearray()
    for ch in raw:
        if ch == 0:
            if cur:
                parts.append(bytes(cur).decode("latin1", "replace"))
                cur = bytearray()
            if len(parts) >= 6:
                break
        elif 32 <= ch < 127:
            cur.append(ch)
        else:
            break
    d["listing"] = "|".join(parts)
    return d


def main():
    root = sys.argv[1]
    out = sys.argv[2]
    rows = []
    files = sorted(f for f in os.listdir(root) if f.endswith(".ifs"))
    for fn in files:
        p = os.path.join(root, fn)
        size = os.path.getsize(p)
        with open(p, "rb") as f:
            head = f.read(0x400)
            d = parse_head(head)
            row = {"file": fn, "size": size}
            row.update(d)
            if d["ok"]:
                tail = d["tail_len"]
                # 采样载荷中部
                if size > 0x400 + 8192 and tail < size:
                    f.seek(max(0xAC, (size - tail) // 2))
                    row["ent"] = entropy(f.read(8192))
                # IWff 位置
                f.seek(0)
                win = f.read(min(0x1000, size))
                i = win.find(b"IWff")
                row["iwff"] = i
            rows.append(row)

    with open(out, "w", encoding="utf-8") as g:
        g.write("kind\tsize\tent\tu16_0a\tiwff\tlisting\tfile\n")
        for r in rows:
            g.write("%s\t%d\t%s\t%s\t%s\t%s\t%s\n" % (
                "nifs" if r.get("ok") else r.get("magic", "?"),
                r["size"],
                ("%.3f" % r["ent"]) if "ent" in r else "-",
                r.get("u16_0a", "-"),
                r.get("iwff", "-"),
                (r.get("listing", "")[:90].replace("\t", " ")),
                r["file"]))

    # 汇总
    kinds = Counter("nifs" if r.get("ok") else r.get("magic", "?") for r in rows)
    print("files=%d" % len(rows))
    for k, v in kinds.most_common(10):
        print("  magic %-10s %d" % (k, v))
    ents = [r["ent"] for r in rows if "ent" in r]
    if ents:
        print("entropy: n=%d min=%.3f max=%.3f avg=%.3f" % (
            len(ents), min(ents), max(ents), sum(ents) / len(ents)))
        lo = [r for r in rows if r.get("ent", 9) < 7.5]
        print("低熵(<7.5) 文件数: %d" % len(lo))
        for r in lo[:20]:
            print("   %.3f  %s" % (r["ent"], r["file"]))


if __name__ == "__main__":
    main()
