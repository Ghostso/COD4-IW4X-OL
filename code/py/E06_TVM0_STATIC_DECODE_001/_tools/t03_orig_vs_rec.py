import pefile, struct, hashlib
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
o=open(ORIG,"rb").read(); po=pefile.PE(ORIG,fast_load=True)
r=open(REC,"rb").read(); pr=pefile.PE(REC,fast_load=True)
om={s.VirtualAddress:s for s in po.sections}; rm={s.VirtualAddress:s for s in pr.sections}
print("=== original vs recovered: same-VA section byte comparison ===")
for va in sorted(set(om)&set(rm)):
    so=om[va]; sr=rm[va]
    a=o[so.PointerToRawData:so.PointerToRawData+min(so.SizeOfRawData,sr.SizeOfRawData)]
    b=r[sr.PointerToRawData:sr.PointerToRawData+min(so.SizeOfRawData,sr.SizeOfRawData)]
    common=sum(1 for x,y in zip(a,b) if x==y)
    print("  VA=0x%08X orig=%-7s rec=%-7s origRaw=0x%X recRaw=0x%X commonBytes=%d/%d" % (
        va,so.Name.rstrip(b"\0").decode(),sr.Name.rstrip(b"\0").decode(),so.SizeOfRawData,sr.SizeOfRawData,common,min(len(a),len(b))))
print()
print("=== does the ORIGINAL also have the .data gap? ===")
for label,pe in (("ORIG",po),("REC",pr)):
    s=[x for x in pe.sections if x.VirtualAddress==0x8F1000][0]
    print("  %s .data: VSize=0x%X RawSize=0x%X -> present=%.3f%%" % (label,s.Misc_VirtualSize,s.SizeOfRawData,100.0*s.SizeOfRawData/s.Misc_VirtualSize))
print()
print("=== is original .data raw == recovered .data raw (byte-identical)? ===")
so=om[0x8F1000]; sr=rm[0x8F1000]
a=o[so.PointerToRawData:so.PointerToRawData+so.SizeOfRawData]
b=r[sr.PointerToRawData:sr.PointerToRawData+sr.SizeOfRawData]
print("  identical:", a==b, " sha_orig", hashlib.sha256(a).hexdigest()[:16], " sha_rec", hashlib.sha256(b).hexdigest()[:16])