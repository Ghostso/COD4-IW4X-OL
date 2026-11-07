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
print('=== 状态1 的另一分支 0x63C85F / 0x63C86E (判据A为真时) ===')
c=rd(0x0063C85F,0x70)
for ins in md.disasm(c,0x0063C85F):
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
    if ins.mnemonic=='ret': break
print()
print('=== 判据A/B 在被调用时的实参来源 (0x63C7F8 附近) ===')
c=rd(0x0063C7F0,0x40)
for ins in md.disasm(c,0x0063C7F0):
    print('   %08X  %-20s %-7s %s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
    if ins.address>0x0063C820: break
