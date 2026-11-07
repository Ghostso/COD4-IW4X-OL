import pefile, re, sys, json, os
p=r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
pe=pefile.PE(p, fast_load=False)
print("machine",hex(pe.FILE_HEADER.Machine),"timestamp",pe.FILE_HEADER.TimeDateStamp,"imagebase",hex(pe.OPTIONAL_HEADER.ImageBase))
print("sections")
for s in pe.sections:
    name=s.Name.rstrip(b"\x00").decode("latin1")
    print(name, hex(s.VirtualAddress), hex(s.Misc_VirtualSize), hex(s.SizeOfRawData), hex(s.PointerToRawData), hex(s.Characteristics))
print("imports")
try:
    for d in pe.DIRECTORY_ENTRY_IMPORT:
        print(d.dll.decode("latin1"), len(d.imports))
except Exception as e: print("import err",e)
print("exports", getattr(pe,"DIRECTORY_ENTRY_EXPORT",None) is not None)
patterns=[b"gamestate",b"configstring",b"snapshot",b"CS_PRIMED",b"CL_Parse",b"CG_Parse",b"CG_ConfigString",b"svc_",b"CL_",b"CG_",b"serverCommand",b"baseline",b"delta",b"parseGamestate",b"ParseGamestate",b"ConfigString",b"Snapshot",b"cgame",b"CG_Init"]
# strings ascii and utf16
def strings(data, minlen=4):
    out=[]
    for m in re.finditer(rb"[\x20-\x7e]{%d,}"%minlen,data):
        out.append((m.start(),m.group().decode("latin1")))
    for m in re.finditer((b"(?:[\x20-\x7e]\x00){%d,}"%minlen),data):
        out.append((m.start(),m.group().decode("utf-16le","replace")))
    return out
allstr=strings(open(p,"rb").read(),4)
# map file offset to rva
def off2rva(off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData+s.SizeOfRawData:
            return s.VirtualAddress+(off-s.PointerToRawData)
    return None
print("matched strings")
seen=set()
for off,s in allstr:
    low=s.lower()
    if any(x.lower() in low for x in ["gamestate","configstring","snapshot","cs_primed","cl_parse","cg_parse","cg_configstring","servercommand","baseline","svc_","parsegamestate"]):
        key=(off,s)
        if key in seen: continue
        seen.add(key)
        print(hex(off), hex(off2rva(off) or 0), repr(s))
