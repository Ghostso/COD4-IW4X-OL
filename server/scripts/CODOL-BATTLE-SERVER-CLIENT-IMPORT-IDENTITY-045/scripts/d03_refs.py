# -*- coding: utf-8 -*-
"""045: find data/indirect references to thunk 0x87BA50 and primitive 0x87BE00; decode remaining ordinal tables."""
import sys, struct, pefile
sys.stdout.reconfigure(encoding="utf-8")
IMG=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
EXE=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
img=open(IMG,"rb").read(); exe=open(EXE,"rb").read(); IB=0x400000
def find_dw(blob,val,limit=20):
    pat=struct.pack("<I",val); out=[];s=0
    while True:
        j=blob.find(pat,s)
        if j<0: break
        out.append(j); s=j+1
        if len(out)>=limit: break
    return out
print("=== dword refs to 0x87BA50 in recovered image (any offset) ===")
for x in find_dw(img,0x87BA50): print("   file off %08X  VA %08X"%(x,IB+x))
print("=== dword refs to 0x87BE00 in recovered image ===")
for x in find_dw(img,0x87BE00): print("   file off %08X  VA %08X"%(x,IB+x))
print()
pe=pefile.PE(r"C:\Windows\SysWOW64\ws2_32.dll", fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
byo={e.ordinal:(e.name.decode() if e.name else None,e.address) for e in pe.DIRECTORY_ENTRY_EXPORT.symbols}
S1_VA,S1_RAW=0x8a8000,0x594000
def eo(rva): return S1_RAW+(rva-S1_VA)
print("=== ordinal tables at 0x8A8370 (6), 0x8A84D4 (23), 0x8A8534 (11) ===")
for start,n in ((0x8A8370,6),(0x8A84D4,23),(0x8A8534,11)):
    print(" table @%08X:"%start)
    for k in range(n):
        v=struct.unpack("<I",exe[eo(start+4*k):eo(start+4*k)+4])[0]
        if v>=0x80000000:
            o=v&0xffff; nm,exp=byo.get(o,(None,None))
            print("   slot VA %08X  ord %3d  %s"%(IB+start+4*k,o,nm))
        else:
            print("   slot VA %08X  name-RVA %08X"%(IB+start+4*k,v))
