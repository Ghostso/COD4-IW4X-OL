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
def cstr(va,n=160):
    b=rd(va,n)
    if b is None or len(b)<2: return None
    e=b.find(b'\x00')
    if e<1: return None
    t=b[:e].decode('latin1')
    return t if all(32<=ord(c)<127 for c in t) else None
print('=== 找所有 *Init@dw* 的 RTTI/符号名 ===')
lo=0x00D80000; hi=0x00EC0000
found=[]
for va in range(lo,hi,4):
    s=cstr(va,160)
    if s and 'Init@dw' in s:
        found.append((va,s))
for va,s in found[:40]:
    print('   0x%08X  %s' % (va,s))
print('   共',len(found))
print()
print('=== 搜所有含 "dwPartyImp" 的串 ===')
i=img.find(b'dwPartyImp',0); n=0
while i>=0 and n<15:
    s=cstr(LO+i,140)
    if s: print('   0x%08X  %s' % (LO+i,s)); n+=1
    i=img.find(b'dwPartyImp',i+1)
