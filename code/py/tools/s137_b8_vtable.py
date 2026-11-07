#!/usr/bin/env python3
"""B8: 顺序 dump 指定 vtable, 直到槽落进数据段; 判纯虚/析构/thunk."""
import struct
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)

# --- PE sections ---
pe = struct.unpack_from("<I", d, 0x3C)[0]
nsec = struct.unpack_from("<H", d, pe + 6)[0]
opt = struct.unpack_from("<H", d, pe + 0x14)[0]
sh = pe + 0x18 + opt
SEC = []
CODE = []   # (lo, hi) 可执行段
for i in range(nsec):
    o = sh + i * 0x28
    nm = d[o:o + 8].rstrip(b"\x00").decode("latin1")
    vsz, va, rsz, raw = struct.unpack_from("<IIII", d, o + 8)
    fl = struct.unpack_from("<I", d, o + 36)[0]
    iscode = bool(fl & 0x20000000) or bool(fl & 0x20)
    SEC.append((nm, 0x400000 + va, vsz, raw, rsz, fl, iscode))
    if iscode:
        CODE.append((0x400000 + va, 0x400000 + va + max(vsz, rsz)))
    print("SEC %-8s VA=%08X VSZ=%08X flags=%08X CODE=%s" % (nm, 0x400000 + va, vsz, fl, iscode))


def rd(va):
    f = va - VA
    if 0 <= f < N - 4:
        return struct.unpack_from("<I", d, f)[0]
    return None


def in_text(va):
    for lo, hi in CODE:
        if lo <= va < hi:
            return True
    return False


def sec_of(va):
    for nm, sva, vsz, raw, rsz, fl, iscode in SEC:
        if sva <= va < sva + max(vsz, rsz):
            return nm + ("(code)" if iscode else "(data)")
    return "?"


def cstr(va, maxlen=120):
    f = va - VA
    if not (0 <= f < N):
        return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > maxlen:
        return None
    s = d[f:e]
    return s.decode("latin1") if s and all(32 <= c < 127 for c in s) else None


def type_name(vt):
    col = rd(vt - 4)
    if not col or not (VA <= col < VA + N):
        return None, None
    ti = rd(col + 0x0C)
    if not ti or not (VA <= ti < VA + N):
        return col, None
    return col, cstr(ti + 8)


def classify(t):
    f = t - VA
    b = d[f:f + 32]
    if b[:1] == b"\xc3":
        return "PURE? ret (c3)"
    if b[:3] == b"\xc2\x04\x00":
        return "PURE? ret 4 (c2 04 00)"
    if b[:1] == b"\xe9":
        return "jmp thunk"
    if b[:2] == b"\x8b\x01" and b[2:4] in (b"\xff\x10", b"\xff\x50"):
        return "mov eax,[ecx];call (虚转发)"
    if b[:3] == b"\x8b\xff\x55":
        return "正常函数 (mov edi,edi;push ebp)"
    return "code"


def dump_vt(vt, label=""):
    col, nm = type_name(vt)
    print("\n" + "=" * 78)
    print("vtable 0x%08X %s  COL=0x%08X  RTTI=%r" % (vt, label, col or 0, nm))
    print("=" * 78)
    slot = 0
    while True:
        t = rd(vt + slot * 4)
        if t is None:
            break
        if not in_text(t):
            print("  [%2d] 0x%08X  <非代码 (%s)>  <-- 边界" % (slot, t, sec_of(t)))
            break
        cls = classify(t)
        print("  [%2d] 0x%08X  %s" % (slot, t, cls))
        code = d[t - VA:t - VA + 24]
        for ins in md.disasm(code, t):
            line = "        0x%08X  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
            for tok in ins.op_str.replace(",", " ").split():
                if tok.startswith("0x"):
                    try:
                        s = cstr(int(tok, 16))
                    except ValueError:
                        s = None
                    if s:
                        line += "   ; '%s'" % s
            print(line)
            if ins.mnemonic.startswith("ret") or ins.mnemonic == "jmp":
                break
        slot += 1
        if slot > 40:
            print("  ... >40 槽, 停")
            break
    print("  => 槽数(以代码段为界) = %d" % slot)


if __name__ == "__main__":
    args = sys.argv[1:] or ["0xDC7BA4", "0xDC7AF4", "0xDC8910", "0xDC8B20", "0xDCCA2C", "0xDCE1D8"]
    for a in args:
        dump_vt(int(a, 0))
