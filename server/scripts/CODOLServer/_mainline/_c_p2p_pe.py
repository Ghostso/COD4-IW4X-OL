import pefile, os
p=r"COD OL\IIPS\p2papp.dll"
pe=pefile.PE(p, fast_load=True)
pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                       pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
print("=== p2papp.dll ===")
print("size",os.path.getsize(p),"ImageBase 0x%X"%pe.OPTIONAL_HEADER.ImageBase,"TimeDate 0x%08X"%pe.FILE_HEADER.TimeDateStamp)
e=pe.DIRECTORY_ENTRY_EXPORT
print("DLL name:", e.name, " exports:", len(e.symbols))
import subprocess
# demangle via undname? just print raw
for s in e.symbols:
    print("   ord %-4s 0x%-7X %s"%(s.ordinal, s.address, s.name.decode() if s.name else ""))
print()
print("=== IMPORTS ===")
for imp in pe.DIRECTORY_ENTRY_IMPORT:
    nm=imp.dll.decode()
    print("   %-20s %d"%(nm, len(imp.imports)))
