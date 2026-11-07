import io
import os
import struct
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "_msg_switcher.log")

buf = io.StringIO()
try:
    sys.path.insert(0, os.path.join(HERE, ".."))
    r = __import__("_recv_gate_disasm")
    img = open(r.IMG, "rb").read()
    BASE = r.BASE
    r.OUT = HERE

    lines = []

    # entry of the message-switcher function containing 0xC761AF
    lines.append("=== head of switcher 0xC76000..0xC76092 ===")
    lines += r.disasm(img, 0xC76000, 0xC76092)

    # jump table entries at 0xC761F2
    lines.append("")
    lines.append("jump table @0xC761F2:")
    for i in range(3):
        v = struct.unpack_from("<I", img, 0xC761F2 - BASE + 4 * i)[0]
        lines.append("  case%d -> 0x%08X" % (i, v))

    # who calls the switcher: first find its true start by scanning back
    # from 0xC76091 for an SEH/std prologue
    o = 0xC76091 - BASE
    start = None
    for back in range(4, 0x200):
        p = o - back
        if img[p:p + 3] == b"\x6a\xff\x68":
            start = p
            break
        if img[p:p + 3] == b"\x55\x8b\xec" and img[p - 1] in (0xCC, 0x90):
            start = p
            break
    fva = BASE + start if start is not None else 0
    lines.append("")
    lines.append("switcher entry ~= 0x%08X" % fva)
    if fva:
        lines += r.disasm(img, fva, min(fva + 0x90, 0xC76092))
        n = len(img)
        # direct near callers
        cal = []
        i = 0
        while True:
            i = img.find(b"\xE8", i, n - 5)
            if i < 0:
                break
            rel = struct.unpack("<i", img[i + 1:i + 5])[0]
            src = BASE + i
            if ((src + 5 + rel) & 0xFFFFFFFF) == fva:
                cal.append(src)
            i += 1
        lines.append("direct callers of switcher: %d" % len(cal))
        for src in cal[:8]:
            lines.append("  --- call at 0x%08X ---" % src)
            lines += r.disasm(img, max(src - 0x50, BASE), src + 0x10)
        # data refs (callback registration)
        t = struct.pack("<I", fva)
        refs = []
        i = 0
        while True:
            i = img.find(t, i, n)
            if i < 0:
                break
            if BASE + i != fva:
                refs.append(BASE + i)
            i += 1
        lines.append("imm32 refs to switcher entry: %d" % len(refs))
        for xa in refs[:10]:
            lines.append("  --- ref at 0x%08X ---" % xa)
            lines += r.disasm(img, max(xa - 0x40, BASE), xa + 0x10)

    r.write_report("msg_switcher.txt", lines)
    buf.write("ok\n")
except Exception:
    buf.write(traceback.format_exc())
open(LOG, "w", encoding="utf-8").write(buf.getvalue())
print("done")
