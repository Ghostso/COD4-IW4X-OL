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
def u32(va):
    b=rd(va,4); return struct.unpack('<I',b)[0] if b and len(b)==4 else None
def cstr(va,n=90):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
md=Cs(CS_ARCH_X86, CS_MODE_32)
print('=== 决定判据: 0x63C5E0 函数最开头的两道闸门 (0x63C5E9) ===')
c=rd(0x0063C5E9,0x30)
for ins in md.disasm(c,0x0063C5E9):
    ann=''
    if '0x' in ins.op_str:
        for tok in ins.op_str.replace(',',' ').split():
            if tok.startswith('0x'):
                try: v=int(tok,16)
                except: continue
                if 0x00C00000<=v<=0x01100000:
                    s=cstr(v,60)
                    if s and len(s)>=3: ann='   ; \"%s\"'%s
    print('   %08X  %-18s %-7s %-28s%s' % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,ann))
print()
print('=== 这两道闸门用 [0x82E13FC] = dwRoomImp 单例 (不是 this!) ===')
g=u32(0x082E13FC)
print('  [0x82E13FC] = 0x%08X' % (g or 0))
if g:
    vt=u32(g)
    print('  vtable = 0x%08X' % (vt or 0))
    for off in (0x60,0x64):
        fn=u32((vt or 0)+off)
        print('    vtable+0x%02X = 0x%08X' % (off, fn or 0))
        if fn:
            b=rd(fn,12)
            print('       函数体: %s' % (b.hex(' ') if b else '?'))
