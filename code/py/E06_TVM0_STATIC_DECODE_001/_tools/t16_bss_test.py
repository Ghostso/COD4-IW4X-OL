import pefile, struct
ORIG=r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"
REC=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
for lbl,P in (("ORIG",ORIG),("REC",REC)):
    pe=pefile.PE(P,fast_load=True)
    print("==== %s ====" % lbl)
    for s in pe.sections:
        nm=s.Name.rstrip(b"\x00").decode()
        ch=s.Characteristics
        init = bool(ch & 0x40); uninit = bool(ch & 0x80)
        print("  %-8s VA=0x%08X VSize=0x%010X Raw=0x%08X  Ch=0x%08X init=%s uninit=%s  tail(BSS)=0x%X bytes" % (
            nm,s.VirtualAddress,s.Misc_VirtualSize,s.SizeOfRawData,ch,init,uninit,
            max(0,s.Misc_VirtualSize-s.SizeOfRawData)))
    print()
print("=== BSS test: is the .data tail necessarily zero-filled by the loader? ===")
print("  PE rule: for VA in [SecVA+RawSize, SecVA+VSize) the loader maps ZERO bytes.")
print("  -> a section with VSize >> RawSize has an implicit BSS tail.")
print()
print("=== sanity: does the 2697 SERVER also have a giant uninitialized section? ===")
SRV=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
pe=pefile.PE(SRV,fast_load=True)
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode()
    if s.Misc_VirtualSize>s.SizeOfRawData:
        print("  SERVER %-8s VSize=0x%X Raw=0x%X tail=0x%X (%.1f MB)" % (nm,s.Misc_VirtualSize,s.SizeOfRawData,s.Misc_VirtualSize-s.SizeOfRawData,(s.Misc_VirtualSize-s.SizeOfRawData)/1048576))