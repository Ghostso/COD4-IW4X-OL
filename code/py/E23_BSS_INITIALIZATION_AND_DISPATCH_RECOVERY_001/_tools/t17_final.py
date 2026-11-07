import struct, pefile
from capstone import *
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
secs=[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections]
def r2f(r):
    for n,va,vs,rp,rs in secs:
        if rp and rp<=r<rp+rs: return n
def sec(r):
    for n,va,vs,rp,rs in secs:
        if va<=r<va+vs: return n
TV=[0xA85AD0,0xA85BE0,0xA85640,0xA87830,0xA878A0]
print("== 4-byte pointer-form scan (VA-form and RVA-form) across whole file ==")
for t in TV:
    for form,val in (("VA",t),("RVA",t-IB)):
        pat=struct.pack("<I",val)
        cnt=d.count(pat)
        print("  %08X %s-form (%08X): %d occurrences"%(t,form,val,cnt))
print()
print("== section attribution matrix ==")
for t in TV:
    print("  VA %08X -> RVA %06X sec=%s rawoff=%s | as-RVA sec=%s (raw none)"%(
        t, t-IB, sec(t-IB), hex(secs and [x for x in secs if x[0]==sec(t-IB)][0] and 0) , sec(t)))
print()
print("== TLS callbacks & .rimp summary ==")
print("  .tls section VA=%08X VS=%08X RS=%08X"%(secs[[x[0] for x in secs].index('.tls')][1],secs[[x[0] for x in secs].index('.tls')][2],secs[[x[0] for x in secs].index('.tls')][4]))
