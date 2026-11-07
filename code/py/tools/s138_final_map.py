#!/usr/bin/env python3
"""s138_final_map: 对 0x636F3C 的 47 个 case, 在"该 case 自身的字节区间"
   (起点=case 地址, 终点=排序后的下一个 case 地址)内扫描:
     (a) mov [reg], imm32 且 imm32 是 dwRoomMessage* vftable  -> 内联构造
     (b) call <fn> 且 <fn> 体内有 (a)                        -> 非内联构造
   再经 COL->TI->RTTI 解出类名。
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

JT = 0x636F3C
CASES = [struct.unpack_from("<I", d, JT - VA + 4 * i)[0] for i in range(0x2F)]
ORDER = sorted(set(CASES))
END = {a: (ORDER[i + 1] if i + 1 < len(ORDER) else 0x636F3C + 0x300)
       for i, a in enumerate(ORDER)}

MOV = re.compile(r"(?:dword ptr )?\[(.+?)\], (0x[0-9a-f]+)$")


def cstr(f):
    e = d.find(b"\x00", f)
    return d[f:e].decode("latin1") if e > 0 else None


def name_of(vt):
    try:
        col = struct.unpack_from("<I", d, vt - VA - 4)[0]
        ti = struct.unpack_from("<I", d, col - VA + 0x0C)[0]
        nm = cstr(ti - VA + 8)
        return nm.replace(".?AV", "").replace(".?AU", "").replace("@@", "") \
            if nm and nm.startswith(".?A") else None
    except Exception:
        return None


def vt_writes(lo, hi):
    out = []
    for ins in md.disasm(d[lo - VA:hi - VA], lo):
        if ins.mnemonic == "mov":
            m = MOV.search(ins.op_str)
            if m:
                imm = int(m.group(2), 16)
                nm = name_of(imm)
                if nm:
                    out.append((ins.address, m.group(1), imm, nm))
    return out


def calls(lo, hi):
    out = []
    for ins in md.disasm(d[lo - VA:hi - VA], lo):
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            t = int(ins.op_str, 16)
            if 0x400000 <= t < 0xD00000:
                out.append((ins.address, t))
    return out


print("| type | handler | 构造点 | 类名 |")
print("|------|---------|--------|------|")
for t in range(0x2F):
    h = CASES[t]
    end = END[h]
    rows = []
    for a, reg, imm, nm in vt_writes(h, end):
        rows.append((a, nm, "inline"))
    for a, tgt in calls(h, end):
        for aa, reg, imm, nm in vt_writes(tgt, tgt + 0x300):
            rows.append((aa, nm, "via 0x%08X" % tgt))
    if not rows:
        print("| 0x%02X | 0x%08X | - | (无构造) |" % (t, h))
        continue
    seen = set()
    for a, nm, how in sorted(rows):
        if (a, nm) in seen:
            continue
        seen.add((a, nm))
        print("| 0x%02X | 0x%08X | 0x%08X | %s |" % (t, h, a, nm))
