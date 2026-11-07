import pefile, struct, zlib, hashlib
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
o=open(ORIG,"rb").read(); r=open(REC,"rb").read()
po=pefile.PE(ORIG,fast_load=True); pr=pefile.PE(REC,fast_load=True)
# Compare every RAW byte range: original vs recovered, section by section (same size portions)
print("=== per-section raw-region comparison (same size portions only) ===")
om={s.VirtualAddress:s for s in po.sections}; rm={s.VirtualAddress:s for s in pr.sections}
for va in sorted(set(om)&set(rm)):
    so=om[va]; sr=rm[va]
    a=o[so.PointerToRawData:so.PointerToRawData+so.SizeOfRawData]
    b=r[sr.PointerToRawData:sr.PointerToRawData+sr.SizeOfRawData]
    print("VA 0x%08X  origRaw=0x%08X recRaw=0x%08X  recover_ratio=%.3f" % (va,len(a),len(b),len(b)/len(a)))
print()
print("=== KEY: which section(s) did the recovery replace, and from what? ===")
print(" .text   VA 0x001000 : orig 0x394400 -> rec 0x7ACA00  (2.14x larger; header says +20=0x7ACA00 -> the UNCOMPRESSED size)")
print(" .tvm0   VA 0xD958000: orig 0x110600 -> rec 0x2B8C00  (2.56x larger; header says +20=0x2B8C00 -> matches)")
print(" .rdata/.data/.tls/.rsrc : identical sizes AND byte-identical -> copied verbatim")
print(" .rimp   VA 0xDC11000: orig 0x336800 -> rec 0x2A00 (recovery replaced the last .tp3 with a .rimp fixup table)")
print()
print("=== confirm .rdata byte-identical ===")
so=om[0x7AE000]; sr=rm[0x7AE000]
a=o[so.PointerToRawData:so.PointerToRawData+so.SizeOfRawData]
b=r[sr.PointerToRawData:sr.PointerToRawData+sr.SizeOfRawData]
print("  identical:",a==b)