import sys, pefile
A=sys.argv[1]; B=sys.argv[2]
a=open(A,"rb").read(); b=open(B,"rb").read()
pe=pefile.PE(A)
print("ImageBase 0x%X"%pe.OPTIONAL_HEADER.ImageBase)
ed=pe.OPTIONAL_HEADER.DATA_DIRECTORY[0]
print("ExportDir RVA 0x%X size 0x%X  fileoff 0x%X"%(ed.VirtualAddress, ed.Size, pe.get_offset_from_rva(ed.VirtualAddress)))
print("Sections:")
secs=[]
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode("latin1")
    secs.append((s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData, nm))
    print("  %-8s VA 0x%06X raw 0x%06X size 0x%06X"%(nm, s.VirtualAddress, s.PointerToRawData, s.SizeOfRawData))
def sec_of(off):
    for va,raw,sz,nm in secs:
        if raw<=off<raw+sz: return nm
    return "?"
diffs=[i for i in range(len(a)) if a[i]!=b[i]]
from collections import Counter
c=Counter(sec_of(o) for o in diffs)
print("diff bytes by section:", dict(c))
# ranges
runs=[]; s=diffs[0]; p=diffs[0]
for x in diffs[1:]:
    if x==p+1: p=x
    else: runs.append((s,p)); s=x; p=x
runs.append((s,p))
print("runs=%d  first/last offsets 0x%X 0x%X"%(len(runs), diffs[0], diffs[-1]))
for (s,e) in runs:
    print("  sec=%-8s off 0x%06X len=%-4d"%(sec_of(s), s, e-s+1))
