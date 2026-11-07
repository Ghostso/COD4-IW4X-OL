"""Hunt every writer of the task-object result fields.

Targets (from VA 0xB98390 / 0xB983A0 / 0xB983B0 accessors):
    [obj + 0x1400]  result code   (checked == 0x22C4 = 8900)
    [obj + 0x240]   status
    [obj + 0x244]   extra struct

Also looks for the immediate constants 0x22C4 / 0x22C7 / 0x2BC / 0x2DE / 0x2DF
and the error/status string keys used by the /auth/ response.
ASCII only.
"""
import re
from collections import defaultdict

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

IMG = (r"CODOLServer\_mainline\_dyn100_run_20260925_182324"
       r"\live\image_best.bin")
d = open(IMG, "rb").read()
base = 0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32)

LO, HI = 0x00400000, 0x00E65000


def dis_at(va, back=10, fwd=24):
    """Disassemble a window that is guaranteed to end at va+6."""
    st = va - back
    out = []
    for ins in md.disasm(d[st - base:va - base + fwd], st):
        if st <= ins.address <= va + fwd:
            out.append(ins)
    return out


def find_disp(disp, name):
    """Find every instruction that references [reg + disp]."""
    print("=" * 74)
    print("### disp 0x%X  (%s)" % (disp, name))
    hits = []
    for pat_name, pat in (("imm32", re.compile(re.escape(
            disp.to_bytes(4, "little")))),):
        for m in pat.finditer(d):
            va = base + m.start()
            if not (LO <= va < HI):
                continue
            ctx = dis_at(va, back=12, fwd=8)
            hits.append((va, ctx))
    wr = []
    rd = []
    for va, ctx in hits:
        text = " | ".join("%s %s" % (i.mnemonic, i.op_str) for i in ctx)
        this = next((i for i in ctx if i.address == va), None)
        if this is None:
            # immediate is the tail of an instruction starting before va
            prev = [i for i in ctx if i.address < va]
            this = prev[-1] if prev else None
        op = "%s %s" % (this.mnemonic, this.op_str) if this else "?"
        is_write = ("mov dword ptr [e" in op and op.rstrip().endswith(
                    "0x%x]" % disp)) or ("mov " in op and op.count("ptr [") == 1
                    and op.index("ptr [") < op.index(","))
        row = (va, op, text)
        (wr if ("mov dword ptr" in op and "0x%x]" % disp in op
                and op.startswith("mov dword ptr [")) else rd).append(row)
    print("-- candidate WRITERS (%d) --" % len(wr))
    for va, op, text in wr:
        print("  0x%08X  %s" % (va, text))
    print("-- other refs (%d, first 40) --" % len(rd))
    for va, op, text in rd[:40]:
        print("  0x%08X  %s" % (va, text))
    print()


for disp, name in ((0x1400, "result code (want 0x22C4=8900)"),
                   (0x240, "status"),
                   (0x244, "extra struct"),
                   (0x2400, "near-status"),
                   (0x2600, "alt-status")):
    find_disp(disp, name)

print("=" * 74)
print("### immediate constants")
for c, name in ((0x22C4, "8900 success"), (0x22C7, "8903 dup-login"),
                (0x2BC, "700 http-ok"), (0x2DE, "734"), (0x2DF, "735"),
                (0x22C5, "8901"), (0x22C6, "8902")):
    pat = re.compile(re.escape(c.to_bytes(4, "little")))
    locs = [base + m.start() for m in pat.finditer(d)
            if LO <= base + m.start() < HI]
    print("%-16s 0x%04X  n=%-3d  %s" % (name, c, len(locs),
          " ".join("0x%08X" % x for x in locs[:14])))
