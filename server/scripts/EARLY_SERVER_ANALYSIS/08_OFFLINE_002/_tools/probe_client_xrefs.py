import pefile, re, struct, json, os, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
P=r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"
pe=pefile.PE(P, fast_load=False); IB=pe.OPTIONAL_HEADER.ImageBase
data=open(P,'rb').read()
def off2rva(off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData+s.SizeOfRawData:
            return s.VirtualAddress+(off-s.PointerToRawData)
    return None
def rva2off(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress+s.Misc_VirtualSize:
            return s.PointerToRawData+(rva-s.VirtualAddress)
    return None
targets={
'netchan_established':0x8489ac,
'received_gamestate':0x849238,
'parse_gamestate_begin':0x849358,
'parse_gamestate_badcmd':0x849388,
'parse_gamestate_badclient':0x8493b0,
'configstrings_percent':0x849210,
'nonbaseline_snap':0x848f70,
'cl_getsnapshot_trunc':0x846370,
'g_find_cs_overflow':0x85d13c,
'exe_cs_mismatch':0x84933c,
'exe_awaiting_gs':0x86b724,
'baseline_lower':0x74e784,
}
md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
# scan all executable-ish sections for absolute VA refs
for name,srva in targets.items():
    va=IB+srva
    pat=struct.pack('<I',va)
    hits=[]
    for s in pe.sections:
        if not (s.Characteristics & 0x20000000): continue
        raw=data[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]
        start=0
        while True:
            j=raw.find(pat,start)
            if j<0: break
            rva=s.VirtualAddress+j; hits.append(rva); start=j+1
    print("\n###",name,hex(srva),"VA",hex(va),"hits",len(hits),[hex(x) for x in hits[:30]])
    for hr in hits[:8]:
        off=rva2off(hr)
        if off is None: continue
        begin=max(0,off-96); end=min(len(data),off+160)
        print("  --- xref",hex(hr),"(VA",hex(IB+hr),") ---")
        for ins in md.disasm(data[begin:end], IB+begin):
            mark=' <==REF' if (ins.address <= IB+hr < ins.address+ins.size) else ''
            print("   %08x %-24s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,mark))
