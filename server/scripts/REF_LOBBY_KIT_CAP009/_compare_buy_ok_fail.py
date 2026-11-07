# -*- coding: utf-8 -*-
"""对比"购买成功"与"购买失败"的 SKU —— 找出类别差异。

用户实测: 武器能买, 道具/名片/消耗品都不能买。
假设: 成功的 SKU 在 exe 目录里(有权威 Category), 失败的不在。
"""
import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(ROOT, "lobby_srv.log")
TASKS = os.path.join(ROOT, "lobby_tasks.bin")


def scan_fields(pl):
    out = []
    i = 0
    n = len(pl)
    while i < n:
        t = pl[i]
        i += 1
        if t in (0x01, 0x03):
            i += 1
        elif t == 0x06:
            i += 2
        elif t in (0x07, 0x08):
            out.append(struct.unpack_from("<I", pl, i)[0]); i += 4
        elif t in (0x09, 0x0A):
            i += 8
        elif t == 0x10:
            j = pl.find(b"\x00", i)
            if j < 0:
                break
            i = j + 1
        elif t == 0x13:
            if i + 5 > n or pl[i] != 0x08:
                break
            ln = struct.unpack_from("<I", pl, i + 1)[0]
            i += 5 + ln
        else:
            break
    return out


def main():
    cat = {int(e["Id"]): e for e in
           json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                          "r", encoding="utf-8"))}
    exe_ids = set(cat)

    # 从日志提成功/失败的 SKU
    ok = []
    bad = []
    for l in open(LOG, "r", encoding="utf-8", errors="replace"):
        m = re.search(r"购买成功 sku=(\d+)", l)
        if m:
            ok.append(int(m.group(1)))
            continue
        if "Unsupported SKU" in l:
            bad.append(None)   # 失败行不含 sku, 稍后用任务文件补
    ok = sorted(set(ok))
    print("日志里购买成功的 SKU: %s" % ok)
    print("失败行数: %d (日志不含 sku, 下面从任务文件取)" % len(bad))
    print()

    # 任务文件里所有购买 SKU
    raw = open(TASKS, "rb").read()
    off = 0
    allsk = []
    while off + 6 <= len(raw):
        svc = raw[off]; task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) not in ((80, 154), (93, 131)):
            continue
        v = scan_fields(pl)
        if len(v) >= 4 and v[1]:
            allsk.append((svc, v[1]))
    seen = sorted(set(s for _, s in allsk))

    print("%-8s %-10s %-6s %s" % ("sku", "在exe目录", "Cat", "Item"))
    print("-" * 46)
    for s in seen:
        e = cat.get(s)
        if e:
            print("%-8d %-10s %-6d %d" % (s, "是", e["Category"], e["Item"]))
        else:
            print("%-8d %-10s %-6s %s" % (s, "★否", "-", "-"))
    print()
    inx = [s for s in seen if s in exe_ids]
    out = [s for s in seen if s not in exe_ids]
    print("在 exe 目录里: %s" % inx)
    print("★ 不在 exe 目录里: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
