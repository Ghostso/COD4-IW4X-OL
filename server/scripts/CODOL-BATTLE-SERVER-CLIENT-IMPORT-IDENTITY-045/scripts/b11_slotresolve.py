# -*- coding: utf-8 -*-
import sys, struct, pefile
sys.stdout.reconfigure(encoding="utf-8")
exe=open(r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe","rb").read()
def exe_rva(rva):
    if 0x8a8000 <= rva < 0xa16000: return 0x594000+(rva-0x8a8000)
    return None
pe=pefile.PE(r"C:\Windows\SysWOW64\ws2_32.dll", fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
byo={e.ordinal:(e.name.decode() if e.name else None) for e in pe.DIRECTORY_ENTRY_EXPORT.symbols}
print("slot_VA_on_disk\tRVA\tdword\tordinal\tws2_32_name")
for va in (0xCA84E4,0xCA84E8,0xCA84EC,0xCA84F0,0xCA8500,0xCA8510,0xCA8520,0xCA853C):
    rva=va-0x400000
    o=exe_rva(rva)
    if o is None:
        print("%08X\t%08X\t(not sec1)"%(va,rva)); continue
    d=struct.unpack("<I",exe[o:o+4])[0]
    if d>=0x80000000:
        ordn=d&0xffff
        print("%08X\t%08X\t%08X\t%d\t%s"%(va,rva,d,ordn,byo.get(ordn)))
    else:
        print("%08X\t%08X\t%08X\t(name-RVA)\t"%(va,rva,d))
