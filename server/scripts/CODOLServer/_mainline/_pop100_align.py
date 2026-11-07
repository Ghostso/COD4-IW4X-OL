import pefile
from capstone import *
p=r"COD OL\codoMP_client_shipRetail.exe"
b=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
def score(start_va, span=0x60):
    off = start_va - 0x714000
    n=0; bad=0
    for ins in md.disasm(b[off:off+span], start_va):
        n+=1
        if ins.mnemonic in ("invalid",): bad+=1
        if n>=28: break
    return n,bad
def best(target_va, back=0x120):
    print("=== target VA 0x%08X ===" % target_va)
    cands=[]
    for d in range(back):
        s = target_va - d
        n,bad = score(s)
        if n>=20 and bad==0:
            cands.append((d,s,n))
    cands.sort()
    for d,s,n in cands[:6]:
        print("   start 0x%08X (offset -0x%X) insns=%d" % (s,d,n))
    if cands:
        d,s,n = cands[0]
        off = s - 0x714000
        print("   --- disasm from 0x%08X ---" % s)
        c=0
        for ins in md.disasm(b[off:off+0xA0], s):
            mark = "  <<<" if s<=target_va< ins.address+ins.size else ""
            print("     %08X  %-20s %s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
            c+=1
            if c>34: break
best(0x008844A2)
print()
best(0x008444DA)
