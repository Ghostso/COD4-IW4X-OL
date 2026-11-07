import pefile, struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(P); IB=pe.OPTIONAL_HEADER.ImageBase; d=open(P,"rb").read()
def sec2off(rva):
    for s in pe.sections:
        if s.VirtualAddress<=rva<s.VirtualAddress+s.Misc_VirtualSize:
            return s.PointerToRawData+rva-s.VirtualAddress if s.SizeOfRawData and rva-s.VirtualAddress<s.SizeOfRawData else None
print("=== send/sendto/WSASend IAT slots ===")
for e in pe.DIRECTORY_ENTRY_IMPORT:
    for imp in e.imports:
        nm=(imp.name or b"").decode(errors="replace")
        if nm in ("send","sendto","WSASend","WSASendTo","WSARecv","recv","recvfrom"):
            # IAT address
            iat=imp.address
            print("  %-10s %-12s IAT VA %08X RVA %06X"%(e.dll.decode(),nm,iat,iat-IB))
            # find code refs (FF 15 disp32 or FF /2 forms)
