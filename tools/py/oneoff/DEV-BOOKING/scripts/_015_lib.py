# -*- coding: utf-8 -*-
"""015 static toolkit: image_best.bin (base 0x400000) analysis helpers."""
import struct
import sys

from capstone import CS_ARCH_X86, CS_MODE_32, Cs
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

IMG = (r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline"
       r"\_dyn100_run_20260925_182324\live\image_best.bin")
BASE = 0x400000
DATA = open(IMG, "rb").read()
END = BASE + len(DATA)
MD = Cs(CS_ARCH_X86, CS_MODE_32)
MD.detail = True


def dis(start, end):
    off = start - BASE
    if off < 0 or off >= len(DATA):
        return []
    code = DATA[off:off + (end - start)]
    return list(MD.disasm(code, start))


def show(start, end, indent=""):
    for ins in dis(start, end):
        note = ""
        for op in ins.operands:
            if op.type == X86_OP_IMM and BASE <= op.imm < END:
                s = cstr(op.imm, 64)
                if s:
                    note = '   ; "%s"' % s
        print("%s0x%08X  %-22s %-8s %s%s"
              % (indent, ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, note))


def cstr(va, limit=128):
    off = va - BASE
    if off < 0 or off >= len(DATA):
        return None
    e = DATA.find(b"\x00", off)
    if e < 0 or e - off > limit:
        return None
    raw = DATA[off:e]
    if all(32 <= b < 127 for b in raw) and raw:
        return raw.decode("ascii")
    return None


def find_dword(value):
    pat = struct.pack("<I", value)
    out = []
    i = DATA.find(pat)
    while i >= 0:
        out.append(BASE + i)
        i = DATA.find(pat, i + 1)
    return out


def direct_callers(target):
    out = []
    for i in range(len(DATA) - 5):
        if DATA[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", DATA, i + 1)[0]
        if BASE + i + 5 + rel == target:
            out.append(BASE + i)
    return out


WRITE_MNEM = {
    "mov", "movzx", "movsx", "movsxd", "xchg", "or", "and", "xor",
    "add", "sub", "inc", "dec", "not", "neg", "shl", "shr", "sar",
    "setne", "sete", "setz", "setnz", "movups", "movaps", "movdqu", "movdqa",
    "stosd", "stosb", "movsb", "movsd", "cmovne", "cmove",
}


def scan_disp(disp, base_reg=None, limit=None, start=0, end=None):
    """Find all instructions referencing [reg + disp] and classify read/write.

    Returns list of dicts.
    """
    pat = struct.pack("<I", disp)
    out = []
    pos = 0
    hi = len(DATA) if end is None else end - BASE
    while True:
        i = DATA.find(pat, pos, hi)
        if i < 0:
            break
        pos = i + 1
        va = BASE + i
        best = None
        for back in range(2, 17):
            st = va - back
            if st < BASE:
                continue
            code = DATA[st - BASE: st - BASE + 24]
            ins = next(MD.disasm(code, st), None)
            if ins and ins.address <= va < ins.address + ins.size:
                best = ins
                break
        if best is None:
            continue
        memops = [op for op in best.operands if op.type == X86_OP_MEM]
        if not memops:
            continue
        m = memops[0].mem
        if m.disp != disp or m.index != 0:
            continue
        regname = best.reg_name(m.base) if m.base else None
        if base_reg and regname != base_reg:
            continue
        is_w = (best.operands[0].type == X86_OP_MEM
                and best.mnemonic in WRITE_MNEM)
        out.append({
            "va": best.address,
            "ins": "%s %s" % (best.mnemonic, best.op_str),
            "mem": "[" + (regname or "") + "+0x%X]" % disp,
            "w": is_w,
            "reg": regname,
        })
        if limit and len(out) >= limit:
            break
    return out


def vtable_at(va, count=100):
    out = []
    for n in range(count):
        off = va - BASE + n * 4
        if off + 4 > len(DATA):
            break
        out.append((n, struct.unpack_from("<I", DATA, off)[0]))
    return out


def fmt(v):
    return "0x%08X" % v if v > 0xFFF else str(v)


def cmd_dis(args):
    show(int(args[0], 16), int(args[1], 16))


def cmd_refs(args):
    for a in args:
        v = int(a, 16)
        print("0x%08X refs=%s" % (v, [hex(x) for x in find_dword(v)] or "none"))
        print("0x%08X direct_calls=%s" % (v, [hex(x) for x in direct_callers(v)] or "none"))


def cmd_vtable(args):
    va = int(args[0], 16)
    cnt = int(args[1]) if len(args) > 1 else 100
    for n, v in vtable_at(va, cnt):
        s = cstr(v, 40)
        print("+0x%03X [%02d] 0x%08X%s" % (n * 4, n, v, '  "%s"' % s if s else ""))


def cmd_disp(args):
    disp = int(args[0], 16)
    reg = args[1] if len(args) > 1 else None
    rows = scan_disp(disp, reg)
    w = [r for r in rows if r["w"]]
    r_ = [r for r in rows if not r["w"]]
    print("disp=0x%X reg=%s : %d hits (%d write, %d read)"
          % (disp, reg, len(rows), len(w), len(r_)))
    for r in rows:
        print("  [%s] 0x%08X  %s" % ("W" if r["w"] else "R", r["va"], r["ins"]))


if __name__ == "__main__":
    cmds = {"dis": cmd_dis, "refs": cmd_refs, "vtable": cmd_vtable, "disp": cmd_disp}
    cmds[sys.argv[1]](sys.argv[2:])
