#!/usr/bin/env python3
"""s138_vtslots: disassemble head of every distinct concrete target of the
dwLobbyEventHandler vtable 0xDE07A4, to classify what each opcode really does.
"""
import struct
import sys
import re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def u32(va):
    o = va - VA
    return struct.unpack_from("<I", d, o)[0] if 0 <= o <= N - 4 else None


def cstr(va, ml=80):
    o = va - VA
    if not (0 <= o < N - 1):
        return None
    e = d.find(b"\x00", o)
    if e < 0 or e - o > ml or e - o < 2:
        return None
    s = d[o:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


VT = 0xDE07A4
seen = {}
for off in range(0, 0x124, 4):
    f = u32(VT + off)
    if f is None:
        continue
    body = b""
    o = f - VA
    if 0 <= o < N:
        body = d[o:o + 10]
    stub = body.startswith(b"\xc3") or body.startswith(b"\xb8") and len(body) > 5 and body[5] == 0xC3
    exe = f
    # follow a single jmp rel32 thunk
    if body[:1] == b"\xe9":
        rel = struct.unpack_from("<i", d, o + 1)[0]
        exe = f + 5 + rel
        j = d[exe - VA:exe - VA + 10]
        if j[:1] == b"\xe9":
            rel2 = struct.unpack_from("<i", d, exe - VA + 1)[0]
            exe = exe + 5 + rel2
    info = ""
    if not stub:
        ins = list(md.disasm(d[exe - VA:exe - VA + 0x40], exe))[:9]
        info = " | ".join("%s %s" % (x.mnemonic, x.op_str) for x in ins[:5])
        strs = [cstr(int(m.group(1), 16)) for m in re.finditer(r"0x([0-9a-f]{6,8})", info)
                for _ in [0]]
        strs = [s for s in strs if s]
        if strs:
            info += "  " + repr(strs[:3])
    seen.setdefault(off, (f, exe, stub, info))

for off in sorted(seen):
    f, exe, stub, info = seen[off]
    print("vt+0x%03X %s 0x%08X%s\n      %s"
          % (off, "STUB" if stub else "    ", f, "" if exe == f else " -> 0x%08X" % exe, info))
