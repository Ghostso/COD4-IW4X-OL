import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = r'run_codol_001\runs\EARLIEST_20261027_123806'
LO = 0x00010000
img = open(os.path.join(D,'snap_002.bin'),'rb').read()
cov = open(os.path.join(D,'snap_002_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=90):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== 确认 0x4F37A0 是 Cmd_AddCommand 类函数 ===')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86, CS_MODE_32)
c=rd(0x004F37A0,0x30)
for ins in md.disasm(c,0x004F37A0):
    print('   %08X  %-16s %-7s %s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
    if ins.mnemonic=='ret': break
print()
print('=== 0x63B0F0 这个函数的调用者 ===')
i=img.find(b'\xE8', 0x400000-LO, 0x0EA59000-LO)
out=[]
while i>=0:
    if all(cov[i+k]==1 for k in range(5)):
        rel=struct.unpack_from('<i',img,i+1)[0]
        if LO+i+5+rel==0x0063B0F0: out.append(LO+i)
    i=img.find(b'\xE8',i+1,0x0EA59000-LO)
print('  ', [hex(x) for x in out] or '无')
print()
print('=== room.match.* 命令串还有谁引用 ===')
for s in (0x00DC6D8C,0x00DC6DA0,0x00DC6DB4,0x00DC6DC4):
    t=cstr(s)
    pat=struct.pack('<I',s)
    i=img.find(pat,0); n=0; hits=[]
    while i>=0 and n<8:
        if all(cov[i+k]==1 for k in range(4)):
            hits.append(hex(LO+i)); n+=1
        i=img.find(pat,i+1)
    print('  %-22s @0x%08X  引用: %s' % (t,s,hits or '无'))
