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
def cstr(va,n=90):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
md=Cs(CS_ARCH_X86, CS_MODE_32)
print('=== 0x005D32B0 的调用者 ===')
i=img.find(b'\xE8', 0x400000-LO, 0x0EA59000-LO)
out=[]
while i>=0:
    if all(cov[i+k]==1 for k in range(5)):
        rel=struct.unpack_from('<i',img,i+1)[0]
        if LO+i+5+rel==0x005D32B0: out.append(LO+i)
    i=img.find(b'\xE8',i+1,0x0EA59000-LO)
print('  ', [hex(x) for x in out] or '无')
print()
print('=== 该函数引用的所有 "xxx" 字符串 (推断语义) ===')
seen=[]
for ins in md.disasm(rd(0x005D32B0,0x400), 0x005D32B0):
    if '0x' in ins.op_str:
        for tok in ins.op_str.replace(',',' ').split():
            if tok.startswith('0x'):
                try: v=int(tok,16)
                except: continue
                if 0x00400000<=v<=0x01100000:
                    s=cstr(v,40)
                    if s and 3<=len(s)<=24 and s not in seen and all(32<=ord(c)<127 for c in s):
                        seen.append(s)
print('  ', seen)
print()
print('=== 0x005D32B0 函数末尾 (看返回值) ===')
c=rd(0x005D3600,0x120)
for ins in md.disasm(c,0x005D3600):
    if ins.mnemonic=='ret':
        print('  ret @ 0x%08X' % ins.address); break
