import struct, pefile
from pathlib import Path
def secs_of(p):
    pe=pefile.PE(p,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
    return IB,[(s.Name.rstrip(b"\0").decode(errors="replace"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData) for s in pe.sections], pe
cands=[
 ("packed 2.6.9.7", r"D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe"),
 ("recovered 2.6.9.7", r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"),
]
for label,p in cands:
    pp=Path(p)
    if not pp.exists(): print(label,"MISSING"); continue
    IB,secs,pe=secs_of(p); d=pp.read_bytes()
    print("=== %s IB=%08X SizeOfImage=%08X ==="%(label,IB,pe.OPTIONAL_HEADER.SizeOfImage))
    for nm,va,vs,rp,rs in secs: print("    %-8s VA=%08X VS=%08X RAW=%08X RS=%08X"%(nm,va,vs,rp,rs))
    for va in (0xC5B13C,0xC5B144,0xD5A4E0,0xD5A4E8):
        r=va-IB; hit=None
        for nm,sva,svs,srp,srs in secs:
            if sva<=r<sva+svs:
                o=srp+(r-sva) if (srs and r-sva<srs) else None
                if o is not None: hit=(nm,d[o:o+24])
                else: hit=(nm,None)
                break
        print("    VA %08X -> %s"%(va, (hit[0], hit[1]) if hit else "outside"))
    print()
