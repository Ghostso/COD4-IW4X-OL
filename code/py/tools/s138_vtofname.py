#!/usr/bin/env python3
"""s138_vtofname: given RTTI short-name substrings, locate type_info, COL, vtable; dump slots with head disasm."""
import re, struct, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
d = open(E, "rb").read(); N = len(d); VA = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)


def u32(va):
    f = va - VA
    return struct.unpack_from("<I", d, f)[0] if 0 <= f <= N - 4 else None


def find_ptr(target, limit=40):
    pat = struct.pack("<I", target); out = []; i = 0
    while True:
        j = d.find(pat, i)
        if j < 0: break
        out.append(VA + j); i = j + 1
        if len(out) >= limit: break
    return out


def cstr(va, ml=80):
    f = va - VA
    if not (0 <= f < N - 1): return None
    e = d.find(b"\x00", f)
    if e < 0 or e - f > ml: return None
    s = d[f:e]
    return s.decode("latin1") if all(32 <= c < 127 for c in s) else None


def dis1(va):
    out = []
    for ins in md.disasm(d[va - VA:va - VA + 0x120], va):
        out.append("      0x%08X %-16s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if ins.mnemonic.startswith("ret") or len(out) >= 10:
            break
    return out


def resolve_name(name_va):
    print("## RTTI name @0x%08X = %r" % (name_va, cstr(name_va)))
    # TypeDescriptor: [vfptr][spare][nameptr]; nameptr points just after the '.[?]' prefix.
    # The stored name ptr often points to the string start (".?AV...") - search both.
    cands = [p for p in find_ptr(name_va) if p < name_va and name_va - p < 0x80]
    if not cands:
        print("   no TD found")
        return
    for c in cands:
        td = c - 8
        print("   TypeDescriptor @0x%08X" % td)
        for col in find_ptr(td, 10):
            sig = u32(col); off = u32(col + 4); cd = u32(col + 8); tdp = u32(col + 12)
            print("     COL @0x%08X sig=%s off=%s cd=%s td=%s" % (col, sig, off, cd, hex(tdp) if tdp else None))
            for vp in find_ptr(col, 8):
                vt = vp + 4
                print("       vtable @0x%08X (pobj=%d)" % (vt, off or 0))
                i = 0
                while i < 40:
                    p = u32(vt + 4 * i)
                    if p is None or not (0x401000 <= p < VA + N):
                        break
                    print("         slot[%2d] (+0x%02X) 0x%08X" % (i, 4 * i, p))
                    i += 1


for pat in sys.argv[1:]:
    b = pat.encode()
    print("\n############ searching %r" % pat)
    seen = set()
    for m in re.finditer(re.escape(b), d):
        va = VA + m.start()
        s = cstr(va, 200)
        if s and s.startswith(".?A"):
            if va in seen: continue
            seen.add(va)
            resolve_name(va)
            break
    if not seen:
        print("   no RTTI for %r" % pat)
