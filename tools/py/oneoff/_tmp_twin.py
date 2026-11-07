import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=110):
    b=rd(va,n)
    if not b: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
md=Cs(CS_ARCH_X86, CS_MODE_32)
print('=== 0x0062CAF0 起: 与 0x006300C0 同型的"读dvar写对象" ===')
code=rd(0x0062CAF0,0x60)
for ins in md.disasm(code,0x0062CAF0):
    ann=''
    if '0x' in ins.op_str:
        for tok in ins.op_str.replace(',',' ').split():
            if tok.startswith('0x'):
                try: v=int(tok,16)
                except: continue
                if 0x00C00000<=v<=0x01000000:
                    s=cstr(v)
                    if s and len(s)>=4: ann='; \"%s\"'%s
    print('  %08X  %-22s %-7s %-34s%s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, ann))
print()
print('=== 0x0047A950 起 (读法不同的那处) ===')
code=rd(0x0047A940,0x50)
for ins in md.disasm(code,0x0047A940):
    print('  %08X  %-22s %-7s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
