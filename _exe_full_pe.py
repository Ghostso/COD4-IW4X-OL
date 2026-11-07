import sys
from pathlib import Path
import pefile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

root = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
p = root / "COD OL" / "codoMP_client_shipRetail.exe"
pe = pefile.PE(str(p), fast_load=False)

print("=== DOS/NT/OPTIONAL ===")
print("ImageBase", hex(pe.OPTIONAL_HEADER.ImageBase))
print("EntryPoint", hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint))
print("SizeOfImage", hex(pe.OPTIONAL_HEADER.SizeOfImage))
print("Subsystem", pe.OPTIONAL_HEADER.Subsystem)
print("DllCharacteristics", hex(pe.OPTIONAL_HEADER.DllCharacteristics))

print("\n=== SECTIONS ===")
for s in pe.sections:
    print(s.Name.rstrip(b"\x00").decode("latin1"), "VA", hex(s.VirtualAddress), "VS", hex(s.Misc_VirtualSize), "RAW", hex(s.PointerToRawData), "RS", hex(s.SizeOfRawData), "CH", hex(s.Characteristics))

print("\n=== DATA DIRECTORIES ===")
for i in range(16):
    d = pe.OPTIONAL_HEADER.DATA_DIRECTORY[i]
    if d.VirtualAddress or d.Size:
        print(i, pefile.DIRECTORY_ENTRY.get(i, ""), hex(d.VirtualAddress), hex(d.Size))

print("\n=== DIRECTORY PARSED ===")
for name in ["IMPORT", "EXPORT", "TLS", "DEBUG", "LOAD_CONFIG", "BOUND_IMPORT", "DELAY_IMPORT", "EXCEPTION", "SECURITY", "RELOCATION"]:
    attr = "DIRECTORY_ENTRY_" + name
    print(name, "present?", hasattr(pe, attr))

print("\n=== TLS RAW READ ===")
tls_va = pe.OPTIONAL_HEADER.DATA_DIRECTORY[9].VirtualAddress
if tls_va:
    rva = tls_va
    off = pe.get_offset_from_rva(rva)
    print("TLS dir rva", hex(rva), "off", hex(off))
    data = pe.__data__[off : off + 40]
    print("TLS raw", data.hex())

print("\n=== PDB ===")
for d in getattr(pe, "DIRECTORY_ENTRY_DEBUG", []):
    try:
        entry = d.entry
        pdb = getattr(entry, "PdbFileName", None)
        print(pdb)
    except Exception as e:
        print("debug err", e)
