# -*- coding: utf-8 -*-
"""在内存里扫 callsign 表(客户端解密后会有明文)。

扫什么: callsignTitle / callsignNameplate / badgeTable 等表名,
        以及表里的行(如 TITLE_ / pcb_ / pci_ / bdg_ 前缀)。

用法(由 nt10 在大厅连接期间调用, 或独立扫 mem_linear):
    python _scan_callsign_tables_mem.py [memdir]
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
NEEDLES = [b"callsignTitle", b"callsignBackground", b"callsignIcon",
           b"callsignFrame", b"callsignNameplate", b"item_cnc",
           b"badgeTable", b"rankIconTable", b"cardNameplate",
           b"cardBackground", b"cardFrame", b"cardIcon"]


def scan(buf, label, out):
    for nd in NEEDLES:
        i = 0
        while True:
            i = buf.find(nd, i)
            if i < 0:
                break
            lo = max(0, i - 80)
            hi = min(len(buf), i + 160)
            ctx = buf[lo:hi]
            strs = re.findall(rb"[ -~]{3,}", ctx)
            out.append((label, nd.decode(), i,
                        b" | ".join(strs).decode("latin1")[:180]))
            i += len(nd)


def main():
    memdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mem_linear")
    out = []
    files = 0
    if os.path.isdir(memdir):
        for fn in sorted(os.listdir(memdir)):
            p = os.path.join(memdir, fn)
            if not os.path.isfile(p):
                continue
            try:
                b = open(p, "rb").read()
            except Exception:
                continue
            files += 1
            scan(b, fn, out)
    print("扫 %d 个区, 命中 %d" % (files, len(out)))
    for label, nd, off, ctx in out[:80]:
        print("  %s %s @0x%X" % (label, nd, off))
        print("      %s" % ctx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
