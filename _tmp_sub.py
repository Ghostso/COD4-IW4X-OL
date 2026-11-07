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
def cstr(va,n=140):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
# 找 dwRoom 的 "SubscribeEvent/RegisterEvent" 之类
print('=== 事件框架相关字符串 ===')
for pat in (b'subscribe', b'Subscribe', b'eventHandler', b'EventSink', b'room.match'):
    i=img.find(pat,0); n=0
    while i>=0 and n<6:
        s=cstr(LO+i,90)
        if s: print('   %-14s 0x%08X  %s' % (pat.decode(),LO+i,s[:70])); n+=1
        i=img.find(pat,i+1)
