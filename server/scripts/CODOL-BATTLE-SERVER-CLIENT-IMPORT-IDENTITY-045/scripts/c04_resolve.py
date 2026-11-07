# -*- coding: utf-8 -*-
"""045: decisive API-identity resolution for the slot family used by 0x87BE00 and the 0x87Bxxx net layer."""
import sys, struct, re, pefile
sys.stdout.reconfigure(encoding="utf-8")
EXE=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"
IMG=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
exe=open(EXE,"rb").read(); img=open(IMG,"rb").read()
IB=0x400000
S1_VA,S1_RAW,S1_RS=0x8a8000,0x594000,0x16e000
def exe_off(rva):
    return S1_RAW+(rva-S1_VA) if S1_VA<=rva<S1_VA+S1_RS else None
# ws2_32 export ordinal -> (name, RVA)
pe=pefile.PE(r"C:\Windows\SysWOW64\ws2_32.dll", fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
byo={}
for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
    byo[e.ordinal]=(e.name.decode() if e.name else None, e.address)
print("ws2_32 ImageBase =", hex(pe.OPTIONAL_HEADER.ImageBase))

def disk_dw(rva):
    o=exe_off(rva); return struct.unpack("<I",exe[o:o+4])[0] if o is not None else None
def img_dw(rva):
    o=rva  # img file offset == RVA
    return struct.unpack("<I",img[o:o+4])[0] if 0<=o<=len(img)-4 else None

slots=[0xCA84E4,0xCA84E8,0xCA84EC,0xCA84F0,0xCA84FC,0xCA8500,0xCA8510,0xCA8514,0xCA8518,0xCA851C,
       0xCA8520,0xCA8524,0xCA8528,0xCA852C,0xCA8534,0xCA8538,0xCA853C,0xCA8540,0xCA8544,0xCA8548,
       0xCA854C,0xCA8550,0xCA8554,0xCA8558,0xCA855C]
print()
print("slot_VA   RVA       disk_dword  ordinal  ws2_32_name        export_RVA  img_dword   base(for 0x75xxxxxx)")
for va in slots:
    rva=va-IB
    d=disk_dw(rva); iv=img_dw(rva)
    nm=None; exp=None; base=None
    if d is not None and d>=0x80000000:
        o=d&0xffff
        if o in byo:
            nm,exp=byo[o]
            if iv is not None and iv>=0x70000000 and iv<0x78000000:
                base=iv-exp
    print("%08X  %08X  %-10s  %-7s  %-18s  %-10s  %-10s  %s"%(
        va, rva, ('%08X'%d) if d is not None else 'OOB',
        (str(d&0xffff) if (d is not None and d>=0x80000000) else ''),
        nm or '', ('%X'%exp) if exp is not None else '',
        ('%08X'%iv) if iv is not None else '',
        ('0x%08X'%base) if base is not None else ''))
