# -*- coding: utf-8 -*-
import sys, struct, pefile
sys.stdout.reconfigure(encoding="utf-8")
IMG=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
img=open(IMG,"rb").read()
pe=pefile.PE(r"C:\Windows\SysWOW64\ws2_32.dll", fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
byo={e.ordinal:(e.name.decode() if e.name else None,e.address) for e in pe.DIRECTORY_ENTRY_EXPORT.symbols}
pairs=[(0xCA8534,0x751C9CC0,115),(0xCA853C,0x751C5D50,111),(0xCA8540,0x751C57E0,10),
       (0xCA8544,0x751CEA60,3),(0xCA8548,0x751CC990,23),(0xCA8550,0x751C56E0,9),
       (0xCA8554,0x751CD890,2),(0xCA855C,0x751EFF10,52),(0xCA8514,0x751D2520,12)]
print("slot_VA   img_value   ordinal  ws2_32_name     export_RVA  implied_base")
for va,iv,o in pairs:
    nm,exp=byo[o]
    print("%08X  %08X  %-7d  %-15s  %-10X  %08X"%(va,iv,o,nm,exp,iv-exp))
print("implied bases:", sorted(set(hex(iv-byo[o][1]) for _,iv,o in pairs)))
