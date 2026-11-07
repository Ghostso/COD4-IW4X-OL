"""Lineage of ctx+0x8710 (HTTP status): all writers + callers of the
status-line parser that contains 0xAEDC00 (sscanf "HTTP/1.%d %d").
Also resolve the 0xAD4A70/0xAD4700 jump-table entry for propid 0x200002.
"""
import io
import os
import struct
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "_status_lineage.log")

buf_out = io.StringIO()
try:
    sys.path.insert(0, os.path.join(HERE, ".."))
    r = __import__("_recv_gate_disasm")
    img = open(r.IMG, "rb").read()
    BASE = r.BASE

    def o2v(off):
        return BASE + off

    # ---------------------------------------------------------------
    # 1. writers of [reg32 + 0x8710]
    # ---------------------------------------------------------------
    lines = ["[A] writers of [reg+0x8710]:"]
    d = struct.pack("<I", 0x8710)
    i = 0
    n = len(img)
    hits = []
    while True:
        i = img.find(d, i, n)
        if i < 0:
            break
        if i >= 2:
            op = img[i - 2]
            modrm = img[i - 1]
            mod = (modrm >> 6) & 3
            reg = (modrm >> 3) & 7
            if op == 0x89 and mod == 2:
                hits.append(o2v(i - 2))
            elif op == 0xC7 and mod == 2 and reg == 0:
                hits.append(o2v(i - 2))
        i += 1
    for va in hits:
        lines.append("")
        lines.append("=== writer at 0x%08X ===" % va)
        lines += r.disasm(img, va - 0x50, va + 0x18)
    lines.append("total %d writers" % len(hits))

    # ---------------------------------------------------------------
    # 2. jump-table resolution for propid 0x200002 in 0xAD4700
    # ---------------------------------------------------------------
    lines.append("")
    lines.append("[B] 0xAD4700 numeric getter, propid 0x200002:")
    idx_byte = img[0xAD4844 - BASE + 0]  # index for delta 0
    tgt = struct.unpack_from("<I", img, 0xAD47F8 - BASE + 4 * idx_byte)[0]
    lines.append("  delta=0 -> mapbyte=0x%02X -> case=0x%08X" % (idx_byte, tgt))
    lines += r.disasm(img, tgt, tgt + 0x20)

    # ---------------------------------------------------------------
    # 3. enclosing function of 0xAEDC00 (status parser) and its callers
    # ---------------------------------------------------------------
    # find prologue backwards: "55 8b ec" preceded by int3/nop padding
    va = 0xAEDC00
    start = None
    o = va - BASE
    for back in range(4, 0x600):
        p = o - back
        if img[p:p + 3] == b"\x55\x8b\xec":
            # prefer a clean alignment boundary (prev byte CC or 90)
            prev = img[p - 1]
            if start is None or prev in (0xCC, 0x90):
                start = p
                if prev in (0xCC, 0x90):
                    break
    fva = o2v(start) if start is not None else 0
    lines.append("")
    lines.append("[C] parser function start ~= 0x%08X" % fva)

    # callers: near call rel32 targeting fva
    callers = []
    i = 0
    needle_head = None
    while True:
        i = img.find(b"\xE8", i, n - 5)
        if i < 0:
            break
        rel = struct.unpack("<i", img[i + 1:i + 5])[0]
        src = o2v(i)
        if ((src + 5 + rel) & 0xFFFFFFFF) == fva:
            callers.append(src)
        i += 1
    lines.append("direct callers of parser: %d" % len(callers))
    for src in callers[:8]:
        lines.append("  --- call at 0x%08X ---" % src)
        lines += r.disasm(img, src - 0x40, src + 0x10)

    # ---------------------------------------------------------------
    # 4. also: who references the parser address as data (callback reg)
    # ---------------------------------------------------------------
    refs = []
    if fva:
        t = struct.pack("<I", fva)
        i = 0
        while True:
            i = img.find(t, i, n)
            if i < 0:
                break
            if o2v(i) != 0 and o2v(i) != fva:
                refs.append(o2v(i))
            i += 1
    lines.append("imm32/data refs to 0x%08X: %d" % (fva, len(refs)))
    for xa in refs[:10]:
        lines.append("  --- ref at 0x%08X ---" % xa)
        lines += r.disasm(img, max(xa - 0x30, BASE), xa + 0x10)

    # ---------------------------------------------------------------
    # 5. writers of [reg32 + 0x870C]  (what propid 0x200002 really reads)
    # ---------------------------------------------------------------
    lines.append("")
    lines.append("[D] writers of [reg+0x870C]:")
    d = struct.pack("<I", 0x870C)
    i = 0
    hits8c = []
    while True:
        i = img.find(d, i, n)
        if i < 0:
            break
        if i >= 2:
            op = img[i - 2]
            modrm = img[i - 1]
            mod = (modrm >> 6) & 3
            reg = (modrm >> 3) & 7
            if op == 0x89 and mod == 2:
                hits8c.append((o2v(i - 2), "mov [r+0x870C], reg"))
            elif op == 0xC7 and mod == 2 and reg == 0:
                iv = struct.unpack_from("<I", img, i + 4)[0]
                hits8c.append((o2v(i - 2), "mov dword [r+0x870C], 0x%X" % iv))
        i += 1
    for va, note in hits8c:
        lines.append("")
        lines.append("=== 0x%08X  %s ===" % (va, note))
        lines += r.disasm(img, va - 0x50, va + 0x18)
    lines.append("total %d writers of +0x870C" % len(hits8c))

    # ---------------------------------------------------------------
    # 6. map bytes for propid delta 0..4 (numeric getter 0xAD4700)
    # ---------------------------------------------------------------
    lines.append("")
    lines.append("[E] mapbytes delta 0..4:")
    for dl in range(5):
        mb = img[0xAD4844 - BASE + dl]
        tg = struct.unpack_from("<I", img, 0xAD47F8 - BASE + 4 * mb)[0]
        lines.append("  delta=%d -> mapbyte=0x%02X -> case=0x%08X"
                     % (dl, mb, tg))

    # ---------------------------------------------------------------
    # 7. callers into the parser window [0xAED900, 0xAEDC30)
    # ---------------------------------------------------------------
    lines.append("")
    lines.append("[F] near calls landing in [0xAED900,0xAEDC30):")
    cal = {}
    i = 0
    while True:
        i = img.find(b"\xE8", i, n - 5)
        if i < 0:
            break
        rel = struct.unpack("<i", img[i + 1:i + 5])[0]
        src = o2v(i)
        tgt = (src + 5 + rel) & 0xFFFFFFFF
        if 0xAED900 <= tgt < 0xAEDC30:
            cal.setdefault(tgt, []).append(src)
        i += 1
    for tgt in sorted(cal):
        for src in cal[tgt][:4]:
            lines.append("call from 0x%08X -> 0x%08X" % (src, tgt))
    for tgt in sorted(cal):
        lines.append("")
        lines.append("=== caller context for 0x%08X ===" % tgt)
        s0 = cal[tgt][0]
        lines += r.disasm(img, max(s0 - 0x60, BASE), s0 + 0x10)
    lines.append("targets=%d" % len(cal))

    # ---------------------------------------------------------------
    # 8. find parser function start via SEH prologue scan
    # ---------------------------------------------------------------
    lines.append("")
    o = 0xAEDC00 - BASE
    start = None
    for back in range(4, 0x800):
        p = o - back
        if img[p:p + 3] == b"\x6a\xff\x68":       # push -1; push imm32 (SEH)
            start = p
            break
        if img[p:p + 3] == b"\x55\x8b\xec" and img[p - 1] in (0xCC, 0x90):
            start = p
            break
    fva = o2v(start) if start is not None else 0
    lines.append("[G] relaxed parser prologue start ~= 0x%08X" % fva)
    if fva:
        lines += r.disasm(img, fva, fva + 0x30)
        # refs to that start as callback
        t = struct.pack("<I", fva)
        i = 0
        refs = []
        while True:
            i = img.find(t, i, n)
            if i < 0:
                break
            refs.append(o2v(i))
            i += 1
        lines.append("imm32 refs to parser entry: %d" % len(refs))
        for xa in refs[:8]:
            lines.append("  --- ref at 0x%08X ---" % xa)
            lines += r.disasm(img, max(xa - 0x30, BASE), xa + 0x10)

    r.OUT = HERE
    r.write_report("status_lineage.txt", lines)
    buf_out.write("hits_8710=%d callers=%d refs=%d\n"
                  % (len(hits), len(callers), len(refs)))
except Exception:
    buf_out.write(traceback.format_exc())
open(LOG, "w", encoding="utf-8").write(buf_out.getvalue())
print("done")
