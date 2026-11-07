#!/usr/bin/env python3
"""s138_vt_refs: 全镜像找所有 `mov dword ptr [reg], imm32` 且 imm32 是合法
   dwRoomMessage* vftable; 解出类名 + 引用点。
   同时也找 `push imm32` 形式的构造点。
"""
import re
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)


def cstr(va, maxlen=200):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def name_of(vt):
    f = vt - VA - 4
    if not (0 <= f < N - 4):
        return None
    col = struct.unpack_from("<I", d, f)[0]
    cf = col - VA + 0x0C
    if not (0 <= cf < N - 4):
        return None
    ti = struct.unpack_from("<I", d, cf)[0]
    nm = cstr(ti + 8)
    if nm and nm.startswith(".?AV"):
        return nm.replace(".?AV", "").replace("@@", "")
    return None


LO, HI = 0xDC0000, 0xDD0000
seen = {}
pat = re.compile(rb"\xc7[\x00-\x3f\x80-\xbf]", re.S)
# 扫 mov [reg+disp], imm32  (C7 /0)
for m in pat.finditer(d):
    p = m.start()
    # modrm
    modrm = d[p + 1]
    mod = modrm >> 6
    rm = modrm & 7
    off = p + 2
    if mod == 0 and rm == 5:
        off += 4           # disp32, no reg
        if d[off - 4] == 0 and False:
            pass
        reg_expr = None
    elif mod == 1:
        off += 1
        reg_expr = None
    elif mod == 2:
        off += 4
        reg_expr = None
    else:
        reg_expr = None
    if off + 4 > N:
        continue
    imm = struct.unpack_from("<I", d, off)[0]
    if not (LO <= imm < HI):
        continue
    nm = name_of(imm)
    if not nm:
        continue
    seen.setdefault(imm, []).append((VA + p, nm))

print("| vftable | 类名 | mov [reg],imm32 引用点 |")
print("|---------|------|------------------------|")
for vt in sorted(seen):
    refs = seen[vt]
    print("| 0x%08X | %s | %s |" % (
        vt, refs[0][1], ", ".join("0x%08X" % a for a, _ in refs)))
print("\n共 %d 个 vftable 被 mov 立即数引用" % len(seen))
