#!/usr/bin/env python3
"""s138_ctor_typeid: 直接读出每个 dwRoomMessage 子类的消息类型号。

铁证两条:
  (a) 序列化器 0x628320: `mov al,[esi+4]; writeCode(3); writeData(&al,8)`
      => [obj+4] 就是 8 位消息类型号。
  (b) 构造模板固定为
        mov dword ptr [obj+4], <k>
        mov dword ptr [obj],   <vftable>
      例(0x635B47 起):
        0x635B51  mov dword ptr [ebp - 0x3b4], 0x1d
        0x635B5B  mov dword ptr [ebp - 0x3b8], 0xdc754c  -> MemberDetails
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

# 形如 "dword ptr [ebp - 0x3b8], 0xdc754c" / "[esi + 4], 6"
MOV = re.compile(
    r"\[(\w+)(?: ?([+-]) ?(0x[0-9a-f]+|[0-9]+))?\], (-?0x[0-9a-f]+|-?[0-9]+)")


def num(s):
    s = s.strip()
    if "0x" in s:
        return int(s, 16)
    return int(s, 10)


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


def scan(lo, hi):
    out = []
    for ins in md.disasm(d[lo - VA:hi - VA], lo):
        if ins.mnemonic == "ret" or ins.mnemonic.startswith("ret"):
            break
        if ins.mnemonic != "mov":
            continue
        m = MOV.search(ins.op_str)
        if not m:
            continue
        base, sign, dh, v = m.groups()
        disp = 0
        if dh is not None:
            disp = num(dh) * (-1 if sign == "-" else 1)
        out.append((ins.address, base, disp, num(v)))
    return out


JT = 0x636F3C
CASES = [struct.unpack_from("<I", d, JT - VA + 4 * i)[0] for i in range(0x2F)]
ORDER = sorted(set(CASES))
END = {a: (ORDER[i + 1] if i + 1 < len(ORDER) else 0x636F3C + 0x300)
       for i, a in enumerate(ORDER)}

print("| type(表) | handler | 构造点 | [obj+4] 写入 | vftable | 类名 |")
print("|-----------|---------|--------|--------------|---------|------|")
own = {}
for t in range(0x2F):
    h = CASES[t]
    ms = scan(h, END[h])
    rows = []
    for addr, base, disp, val in ms:
        if not (0xDC7000 <= val < 0xDC7800):
            continue
        nm = name_of(val)
        if not nm or "dwRoomMessage" not in nm:
            continue
        # 对象基址 = base+disp; 类型号写在该基址 +4
        tid = None
        for a2, b2, d2, v2 in ms:
            if b2 == base and d2 == disp + 4 and a2 < addr and addr - a2 < 0x20:
                tid = v2
        rows.append((addr, val, nm, tid))
    for addr, vt, nm, tid in rows:
        own.setdefault(nm, set()).add(tid)
        print("| 0x%02X | 0x%08X | 0x%08X | %s | 0x%08X | %s |" % (
            t, h, addr,
            ("0x%02X (%d)" % (tid, tid)) if tid is not None else "-", vt, nm))

print("\n=== 类 -> 构造器写入的类型号集合(直接读数, 非推断) ===")
for nm in sorted(own, key=lambda k: sorted(x for x in own[k] if x is not None)):
    vals = sorted(v for v in own[nm] if v is not None)
    print("  %-48s %s" % (nm, ", ".join("0x%02X" % v for v in vals) or "(未捕获)"))
