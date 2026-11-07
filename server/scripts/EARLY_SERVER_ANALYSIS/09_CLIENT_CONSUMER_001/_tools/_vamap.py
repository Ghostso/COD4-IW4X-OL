import pefile, struct
p=r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
data=open(p,"rb").read()
pe=pefile.PE(p, fast_load=True)
ib=pe.OPTIONAL_HEADER.ImageBase
secs=[]
for s in pe.sections:
    secs.append((s.Name.rstrip(b"\x00").decode(errors="replace"), s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData))
def off2va(off):
    for n,va,vs,raw,rs in secs:
        if raw<=off<raw+rs:
            return ib+va+(off-raw)
    return None
def va2off(va):
    rva=va-ib
    for n,sva,vs,raw,rs in secs:
        if sva<=rva<sva+rs:
            return raw+(rva-sva)
    return None
strings={
 'netchan_t established':'netchan_t established',
 'Received gamestate':'Received gamestate from server',
 'CL_ParseGamestate begin':'CL_ParseGamestate: begin parse',
 'bad command byte':'bad command byte',
 'configStrings:':'configStrings:',
 'ignoring illegible':'ignoring illegible message',
 'G_FindConfigstringIndex':'G_FindConfigstringIndex',
 'CL_GetSnapshot truncated':'CL_GetSnapshot: truncated',
 'non-SNAPFLAG_BASELINE':'non-SNAPFLAG_BASELINE',
 'EXE_AWAITINGGAMESTATE':'EXE_AWAITINGGAMESTATE',
 'EXE_CONFIGSTRINGMISMATCH':'EXE_CONFIGSTRINGMISMATCH',
}
for k,s in strings.items():
    pat=s.encode()
    offs=[]
    i=data.find(pat)
    while i!=-1:
        offs.append(i); i=data.find(pat,i+1)
    print("%-24s n=%d" % (k,len(offs)))
    for o in offs[:6]:
        va=off2va(o)
        # pointer refs to this va
        refs=[]
        if va is not None:
            pb=struct.pack("<I",va)
            j=data.find(pb)
            while j!=-1:
                refs.append(j); j=data.find(pb,j+1)
        print("   off=0x%x va=%s ptrrefs=%s" % (o, hex(va) if va else None, [hex(r) for r in refs[:6]]))
