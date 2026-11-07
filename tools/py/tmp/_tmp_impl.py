import os, sys, struct
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
D = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\EARLIEST2_20261027_132645'
LO = 0x00010000
img=open(os.path.join(D,'snap_004.bin'),'rb').read()
cov=open(os.path.join(D,'snap_004_cover.bin'),'rb').read()
def rd(va,n):
    o=va-LO
    if o<0 or o+n>len(img) or sum(cov[o:o+n])!=n: return None
    return img[o:o+n]
def cstr(va,n=110):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
md=Cs(CS_ARCH_X86, CS_MODE_32)
print('=== setdvar 实现 0x005F49F0 ===')
c=rd(0x005F49F0,0x90)
n=0
for ins in md.disasm(c,0x005F49F0):
    ann=''
    if '0x' in ins.op_str:
        for tok in ins.op_str.replace(',',' ').split():
            if tok.startswith('0x'):
                try: v=int(tok,16)
                except: continue
                if 0x00C00000<=v<=0x01100000:
                    s=cstr(v,70)
                    if s and len(s)>=3: ann='   ; \"%s\"'%s
    print('   %08X  %-20s %-7s %-30s%s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann))
    n+=1
    if ins.mnemonic=='ret' or n>30: break
print()
print('=== 对照: 这片表是谁在用 (找到遍历它的代码就能确认是脚本注册) ===')
pat=struct.pack('<I',0x00DAA5F0)
i=img.find(pat,0); n=0
while i>=0 and n<6:
    if all(cov[LO-i+LO+k- LO]==1 for k in range(4)) if False else True:
        va=LO+i
        if 0x400000<=va<0x0EA59000:
            print('   引用 @0x%08X' % va); n+=1
    i=img.find(pat,i+1)
print('   共',n)
