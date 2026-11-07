# -*- coding: utf-8 -*-
"""020: static reconstruction of the Lobby message dispatcher (marker 0x01 vs 0x02).

Read-only. Uses image_best.bin (base 0x400000).
"""
import struct, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _015_lib import DATA, BASE, END, MD, dis, show, cstr, find_dword, direct_callers, vtable_at
from capstone.x86 import X86_OP_IMM, X86_OP_MEM, X86_OP_REG

def rel_refs(target):
    """All E8 (call) and E9 (jmp) rel32 targeting the given address."""
    out = []
    for i in range(len(DATA) - 5):
        if DATA[i] not in (0xE8, 0xE9):
            continue
        rel = struct.unpack_from("<i", DATA, i + 1)[0]
        if BASE + i + 5 + rel == target:
            out.append((BASE + i, "call" if DATA[i] == 0xE8 else "jmp"))
    return out

def refs_full(target):
    print("=== target 0x%08X ===" % target)
    print("  dword refs      :", [hex(x) for x in find_dword(target)] or "none")
    rr = rel_refs(target)
    print("  call/jmp rel32  :", ["%s@0x%X" % (k, a) for a, k in rr] or "none")

def region(a, b):
    show(a, b)



def absrefs(lo, hi):
    """Find every unaligned dword v with lo <= v < hi, and decode the instruction that uses it."""
    hits = []
    for v in range(lo, hi, 4):
        pat = struct.pack("<I", v)
        i = DATA.find(pat)
        while i >= 0:
            hits.append((BASE + i, v))
            i = DATA.find(pat, i + 1)
    hits.sort()
    print("=== absrefs 0x%X..0x%X : %d ===" % (lo, hi, len(hits)))
    for va, v in hits:
        best = None
        for back in range(1, 17):
            st = va - back
            if st < BASE:
                continue
            code = DATA[st - BASE: st - BASE + 24]
            ins = next(MD.disasm(code, st), None)
            if ins and ins.address <= va < ins.address + ins.size:
                best = ins
                break
        if best is None:
            print("  0x%08X -> 0x%08X   (no instruction decoded)" % (va, v))
        else:
            print("  0x%08X -> 0x%08X   %s %s" % (best.address, v, best.mnemonic, best.op_str))


def indcall_disps(a, b):
    """List call/jmp dword ptr [reg+disp] with disp, in [a,b)."""
    from collections import Counter
    insns = list(dis(a, b))
    rows = []
    for i, ins in enumerate(insns):
        if ins.mnemonic != "call" or not ins.op_str.startswith("dword ptr ["):
            continue
        ops = ins.operands
        if not ops or ops[0].type != X86_OP_MEM:
            continue
        m = ops[0].mem
        if m.base == 0 or m.index != 0:
            continue
        prev = insns[i-1] if i else None
        rows.append((ins.address, m.disp, ins.reg_name(m.base), prev))
    c = Counter(d for _, d, _, _ in rows)
    print("=== indcall disps in [0x%X..0x%X) : %d calls, %d distinct disps ===" % (a, b, len(rows), len(c)))
    for d, n in sorted(c.items()):
        print("  disp=0x%-5X count=%d   [%s]" % (d, n, ", ".join("0x%08X" % r[0] for r in rows if r[1] == d)[:150]))

def loadbyte(a, b, disp):
    """Find byte loads from [reg+disp] in [a,b) with 6 instructions of context."""
    print("=== byte loads [reg+0x%X] in [0x%X..0x%X) ===" % (disp, a, b))
    insns = list(dis(a, b))
    for i, ins in enumerate(insns):
        if ins.mnemonic not in ("mov", "movzx", "movsx"):
            continue
        if "byte ptr [" not in ins.op_str:
            continue
        ops = ins.operands
        if not ops or ops[0].type != X86_OP_REG:
            continue
        found = False
        for op in ops[1:]:
            if op.type == X86_OP_MEM and op.mem.disp == disp and op.mem.index == 0:
                found = True
        if not found:
            continue
        print("  --- 0x%08X  %s %s" % (ins.address, ins.mnemonic, ins.op_str))
        for j in range(i + 1, min(len(insns), i + 7)):
            print("        0x%08X  %s %s" % (insns[j].address, insns[j].mnemonic, insns[j].op_str))

def fstart(va, back=0x1200):
    """Scan backwards for the most likely function prologue."""
    pats = [bytes.fromhex("8bff558bec"), bytes.fromhex("558bec"), bytes.fromhex("5589e5")]
    best = None
    for p in pats:
        i = DATA.rfind(p, max(0, va - BASE - back), va - BASE)
        while i >= 0:
            cand = BASE + i
            if best is None or cand > best:
                best = cand
            i = DATA.rfind(p, max(0, va - BASE - back), i)
        if best is not None:
            break
    return best

def sweep(a, b, title=""):
    """Robust linear sweep that skips undecodable bytes."""
    if title:
        print("=== %s ===" % title)
    pa = a
    cur = a
    while cur < b:
        ins = next(MD.disasm(DATA[cur - BASE: b - BASE], cur), None)
        if ins is None:
            cur += 1
            continue
        note = ""
        for op in ins.operands:
            if op.type == X86_OP_IMM and BASE <= op.imm < END:
                s = cstr(op.imm, 48)
                if s:
                    note = '   ; "%s"' % s
        print("  0x%08X  %-20s %s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, note))
        cur = ins.address + ins.size

def vcalls(a, b, disp):
    """Linear-disassemble [a,b) and report indirect call/jmp [reg+disp] with context."""
    print("=== vcalls [0x%X..0x%X) disp=0x%X ===" % (a, b, disp))
    insns = list(dis(a, b))
    for i, ins in enumerate(insns):
        if ins.mnemonic not in ("call", "jmp"):
            continue
        if not ins.op_str.startswith("dword ptr ["):
            continue
        ops = ins.operands
        if not ops or ops[0].type != X86_OP_MEM:
            continue
        if ops[0].mem.disp != disp:
            continue
        print("  --- 0x%08X  %s %s" % (ins.address, ins.mnemonic, ins.op_str))
        for j in range(max(0, i - 8), i + 1):
            print("        0x%08X  %-20s %s" % (insns[j].address, insns[j].bytes.hex(), insns[j].mnemonic + " " + insns[j].op_str))

def patr(lo, hi, pats):
    """Like pat() but only report hits whose address is in [lo,hi)."""
    for ps in pats:
        pb = bytes.fromhex(ps)
        i = DATA.find(pb)
        while i >= 0:
            va = BASE + i
            if lo <= va < hi:
                print("  0x%08X  %s" % (va, ps))
            i = DATA.find(pb, i + 1)

def pat(pats, ctx=32):
    """Find literal byte patterns; print address + disassembly context."""
    for ps in pats:
        pb = bytes.fromhex(ps)
        i = DATA.find(pb)
        n = 0
        print("--- pattern %s ---" % ps)
        while i >= 0:
            va = BASE + i
            print("  0x%08X" % va)
            for ins in dis(va - 12, va + ctx):
                mark = " <<<" if ins.address == va else ""
                print("      0x%08X  %-20s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic + " " + ins.op_str, mark))
            n += 1
            i = DATA.find(pb, i + 1)
            if n >= 6:
                print("      ... (truncated)")
                break
        if n == 0:
            print("   none")

def idxrefs(lo, hi, want_index=True):
    """Find instructions whose memory operand uses disp in [lo,hi) with a scaled index register."""
    hits = []
    for v in range(lo, hi, 4):
        pat = struct.pack("<I", v)
        i = DATA.find(pat)
        while i >= 0:
            hits.append((BASE + i, v))
            i = DATA.find(pat, i + 1)
    hits.sort()
    n = 0
    print("=== idxrefs 0x%X..0x%X : %d raw ===" % (lo, hi, len(hits)))
    for va, v in hits:
        best = None
        for back in range(1, 17):
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
        if m.disp != v:
            continue
        if want_index and m.index == 0:
            continue
        idx = best.reg_name(m.index) if m.index else None
        bas = best.reg_name(m.base) if m.base else None
        print("  0x%08X  %-24s disp=0x%X base=%s index=%s scale=%d"
              % (best.address, best.mnemonic + " " + best.op_str, v, bas, idx, m.scale))
        n += 1
    print("  -> %d indexed hits" % n)

def dump(a, b, ann=True):
    off = a - BASE
    n = (b - a) // 4
    for k in range(n):
        o = off + k * 4
        v = struct.unpack_from("<I", DATA, o)[0]
        s = cstr(v, 40) if ann else None
        print("0x%08X  [%+5d]  0x%08X%s" % (a + k*4, (a + k*4 - 0xDE080C)//4, v, '  "%s"' % s if s else ""))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "region":
        region(int(sys.argv[2], 16), int(sys.argv[3], 16))
    elif cmd == "refs":
        for a in sys.argv[2:]:
            refs_full(int(a, 16))
    elif cmd == "lb":
        loadbyte(int(sys.argv[2], 16), int(sys.argv[3], 16), int(sys.argv[4], 16))
    elif cmd == "fstart":
        for a in sys.argv[2:]:
            v = int(a, 16)
            print("fstart(0x%X) = 0x%X" % (v, fstart(v) or 0))
    elif cmd == "sweep":
        sweep(int(sys.argv[2], 16), int(sys.argv[3], 16), " ".join(sys.argv[4:]))
    elif cmd == "indd":
        indcall_disps(int(sys.argv[2], 16), int(sys.argv[3], 16))
    elif cmd == "patr":
        patr(int(sys.argv[2], 16), int(sys.argv[3], 16), sys.argv[4:])
    elif cmd == "vcalls":
        vcalls(int(sys.argv[2], 16), int(sys.argv[3], 16), int(sys.argv[4], 16))
    elif cmd == "pat":
        pat(sys.argv[2:])
    elif cmd == "idxrefs":
        idxrefs(int(sys.argv[2], 16), int(sys.argv[3], 16))
    elif cmd == "absrefs":
        absrefs(int(sys.argv[2], 16), int(sys.argv[3], 16))
    elif cmd == "dump":
        dump(int(sys.argv[2], 16), int(sys.argv[3], 16))
    elif cmd == "vt":
        va = int(sys.argv[2], 16); cnt = int(sys.argv[3]) if len(sys.argv) > 3 else 100
        for n, v in vtable_at(va, cnt):
            s = cstr(v, 40)
            print("+0x%03X [%02d] 0x%08X%s" % (n*4, n, v, '  "%s"' % s if s else ""))
