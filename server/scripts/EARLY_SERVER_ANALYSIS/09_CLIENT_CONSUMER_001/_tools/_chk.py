import pefile
EXE = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
data=open(EXE,"rb").read()
pe=pefile.PE(data=data, fast_load=True)
ib=pe.OPTIONAL_HEADER.ImageBase
secs=[]
for s in pe.sections:
    name=s.Name.rstrip(b"\x00").decode("latin1")
    secs.append((name, ib+s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData))
    print("sec %-8s VA=%08x vsize=%08x rawptr=%08x rawsize=%08x" % (name, ib+s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData))
def off_to_va(off):
    for name,va,vs,pr,rs in secs:
        if pr<=off<pr+rs: return va+(off-pr)
    return None
def va_to_off(va):
    for name,v,vs,pr,rs in secs:
        b=v-ib
        if b<=va-ib<b+max(vs,rs): return pr+((va-ib)-b)
    return None
# search the literal strings anywhere in the file
targets = [b"netchan_t established, getting gamestate",
           b"Received gamestate from server",
           b"CL_ParseGamestate: begin parse of gamestate",
           b"bad command byte",
           b"configStrings:",
           b"ignoring illegible message"]
for t in targets:
    idx=data.find(t)
    print("STR %-55s fileoff=%s va=%s" % (t[:50].decode("latin1"), hex(idx) if idx>=0 else None, hex(off_to_va(idx)) if idx>=0 else None))
