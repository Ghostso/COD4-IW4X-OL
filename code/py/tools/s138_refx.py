#!/usr/bin/env python3
"""s138_refx: deterministic absolute-address xref by ModRM decoding (not linear sweep).

For each raw 4-byte LE hit of TGT at file offset j:
  - If d[j-1] is an absolute-address ModRM (mod=00,r/m=101 => reg<<3|5):
      05 0d 15 1d 25 2d 35 3d  -> decode from j-2 (1-byte opcode) or j-3 (0f xx)
    produce the instruction; classify mem read/write/rmw by mnemonic.
  - elif d[j-1] in (0xA1,0xA3): moffs mov eax,[abs] / mov [abs],eax
  - elif d[j-1]==0x68: push imm32 (address taken)
  - elif d[j-1] in (B8..BF): mov reg,imm32 (address taken)
This avoids the classic '83 3d <addr> imm8' vs false '3d <addr>' confusion by
requiring the memory-operand (bracket) form for R/W and mov/push/lea for address.
usage: python -I tools\\s138_refx.py <hexaddr> [--mem|--imm|--all]
"""
import struct
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
E = r"E:\codol_re\client_image_20261027.bin"
VA = 0x400000
d = open(E, "rb").read()
N = len(d)
md = Cs(CS_ARCH_X86, CS_MODE_32)
MODRM_ABS = {0x05, 0x0d, 0x15, 0x1d, 0x25, 0x2d, 0x35, 0x3d}


def hits(t):
    pat = struct.pack("<I", t)
    r = []
    i = 0
    while True:
        j = d.find(pat, i)
        if j < 0:
            break
        r.append(j)
        i = j + 1
    return r


def one(start, tgt):
    """decode one instruction at file offset start; return ins if it covers
    a memory/immediate ref to tgt with a plausible form."""
    ts = "0x%x" % tgt
    for ins in md.disasm(d[start:start + 15], VA + start):
        ops = ins.op_str.lower()
        if ts not in ops:
            return None
        # accept if memory operand OR mov-reg-imm OR push imm OR lea
        if "[" + ts + "]" in ops:
            return ins, "MEM"
        if ins.mnemonic in ("mov", "push", "lea") and ops.rstrip().endswith(ts):
            return ins, "ADDR"
        return None
    return None


def classify(ins):
    mn, ops = ins.mnemonic, ins.op_str.lower()
    ts_bracket = "[" in ops and "0x" in ops
    if mn == "lea":
        return "LEA(取址)"
    if mn == "push":
        return "PUSH(取址)"
    if mn in ("cmp", "test"):
        return "READ"
    if mn == "mov":
        if ops.startswith("dword ptr [") and "," in ops:
            return "WRITE"
        if ops.startswith("byte ptr [") and "," in ops:
            return "WRITE8"
        if ops.startswith("word ptr [") and "," in ops:
            return "WRITE16"
        if "[" in ops.split(",", 1)[0]:
            return "READ"
        return "ADDR"
    if mn in ("inc", "dec", "add", "sub", "or", "and", "xor", "shl", "shr"):
        return "RMW"
    if mn in ("movzx", "movsx"):
        return "READ"
    return mn


def run(tgt, want="all"):
    res = []
    seen = set()
    for j in hits(tgt):
        prev = d[j - 1] if j >= 1 else 0
        starts = []
        if prev in MODRM_ABS:
            starts += [j - 2, j - 3, j - 4]
        if prev in (0xA1, 0xA3):
            starts += [j - 1]
        if prev == 0x68:
            starts += [j - 1]
        if 0xB8 <= prev <= 0xBF:
            starts += [j - 1]
        for st in starts:
            if st < 0:
                continue
            r = one(st, tgt)
            if r:
                ins, kind = r
                key = ins.address
                if key in seen:
                    continue
                seen.add(key)
                res.append((ins, kind))
                break
    res.sort(key=lambda x: x[0].address)
    print("== 0x%08X : %d raw hits, %d decoded refs ==" % (tgt, len(hits(tgt)), len(res)))
    for ins, kind in res:
        c = classify(ins)
        print("  0x%08X  %-22s %-9s %s %s" % (
            ins.address, ins.bytes.hex(), c, ins.mnemonic, ins.op_str))
    # summary counts
    from collections import Counter
    cnt = Counter(classify(i) for i, k in res)
    print("  summary:", dict(cnt))
    print()
    return res


if __name__ == "__main__":
    want = "all"
    args = [a for a in sys.argv[1:]]
    for a in args:
        if a.startswith("--"):
            want = a[2:]
    for a in args:
        if not a.startswith("--"):
            run(int(a, 0), want)
