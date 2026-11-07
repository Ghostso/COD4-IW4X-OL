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
def cstr(va,n=120):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
md=Cs(CS_ARCH_X86, CS_MODE_32)
print('=== setdvar 注册点 0x00644EA3 上下文 ===')
c=rd(0x00644E80,0x50)
for ins in md.disasm(c,0x00644E80):
    ann=''
    if '0x' in ins.op_str:
        for tok in ins.op_str.replace(',',' ').split():
            if tok.startswith('0x'):
                try: v=int(tok,16)
                except: continue
                if 0x00C00000<=v<=0x01100000:
                    s=cstr(v,60)
                    if s and len(s)>=3: ann='   ; \"%s\"'%s
    print('   %08X  %-20s %-7s %-28s%s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann))
print()
print('=== dvar 3291 是否属于"服务器可下发"的 dvar ===')
print('  注册标志 [+0x04] = 0x2000')
print('  对照同族: 3292/1760 也是 0x2000; 1750/1751 是 0x0E0DA091 类')
h=0x0810F7C0
import struct as st
print('  3291 完整前16字节:', rd(h,16).hex(' '))
