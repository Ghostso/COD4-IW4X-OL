import sys, pefile
from capstone import *
A=sys.argv[1]; B=sys.argv[2]
for tag,p in [("BASELINE",A),("INUSE",B)]:
    pe=pefile.PE(p, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    ed=pe.OPTIONAL_HEADER.DATA_DIRECTORY[0]
    print("=== %s  ExportDir RVA 0x%X size 0x%X file 0x%X"%(tag, ed.VirtualAddress, ed.Size, pe.get_offset_from_rva(ed.VirtualAddress)))
    e=pe.DIRECTORY_ENTRY_EXPORT
    for s in e.symbols:
        print("    ord %-4s addr 0x%X  name %s"%(s.ordinal, s.address, s.name))
    # dump the export directory raw bytes
    off=pe.get_offset_from_rva(ed.VirtualAddress)
    print("    raw dir:", open(p,"rb").read()[off:off+ed.Size].hex())
