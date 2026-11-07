# -*- coding: utf-8 -*-
"""Verify the image addressing convention by ASCII-string probing, and the
EXE/DLL/image correspondence. Read-only."""
import sys, os, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
out=[]
def log(s=""): out.append(s)

# 1) probe: for the 042 image, VA X should equal file offset X-0x400000
probes=[("gamestateupdate %d",0x9B4700),("connectResponse",0x9BFF0C),
        ("CG_ServerCommand: ",0x9C61AD),("; net-buffer NOT enough",0x99EE98)]
log("=== file_offset=RVA probe on 17ce image ===")
for s,rva in probes:
    va=C.IBI+rva
    got=C._bi[rva:rva+len(s)]
    log("  VA %08x -> file %08x : %-24s %s" % (va,rva,repr(s), "MATCH" if got==s.encode() else "MISMATCH got=%r"%got[:24]))

# 2) EXE vs image: section table + entry + timestamp
import pefile
pe_exe=pefile.PE(data=C._bex, fast_load=False)
log("")
log("=== EXE (on-disk) vs IMAGE (recovered) ===")
log("  EXE  ImageBase=%08x EP=%08x TimeDateStamp=%08x sections=%s" % (
    pe_exe.OPTIONAL_HEADER.ImageBase, pe_exe.OPTIONAL_HEADER.AddressOfEntryPoint,
    pe_exe.FILE_HEADER.TimeDateStamp, [(s.Name.rstrip(b'\0').decode('latin1'),hex(s.VirtualAddress),hex(s.Misc_VirtualSize)) for s in pe_exe.sections]))
log("  IMG  ImageBase=%08x EP=%08x TimeDateStamp=%08x sections=%s" % (
    C.pe_i.OPTIONAL_HEADER.ImageBase, C.pe_i.OPTIONAL_HEADER.AddressOfEntryPoint,
    C.pe_i.FILE_HEADER.TimeDateStamp, [(s.Name.rstrip(b'\0').decode('latin1'),hex(s.VirtualAddress),hex(s.Misc_VirtualSize)) for s in C.pe_i.sections]))
log("  same ImageBase/EP: %s" % (pe_exe.OPTIONAL_HEADER.ImageBase==C.pe_i.OPTIONAL_HEADER.ImageBase and pe_exe.OPTIONAL_HEADER.AddressOfEntryPoint==C.pe_i.OPTIONAL_HEADER.AddressOfEntryPoint))

# 3) DLL ImageBase + section
log("")
log("=== DLL ===")
log("  DLL ImageBase=%08x sections=%s" % (C.IB,[(s["name"],hex(s["va"])) for s in C.SECTIONS]))

# 4) confirm 042 image coverage vs SizeOfImage
log("")
log("=== image coverage ===")
log("  IMG size=%d (0x%X)  SizeOfImage=0x%X" % (len(C._bi), len(C._bi), C.pe_i.OPTIONAL_HEADER.SizeOfImage))
present=[]
for s in C.pe_i.sections:
    full = (s.PointerToRawData + s.SizeOfRawData) <= len(C._bi)
    present.append((s.Name.rstrip(b'\0').decode('latin1'), hex(s.VirtualAddress), hex(s.Misc_VirtualSize), hex(s.PointerToRawData), hex(s.SizeOfRawData), "FULL" if full else "PARTIAL"))
for p in present: log("  %s"%str(p))

io.open(os.path.join(C.EV,"image_convention_and_correspondence.txt"),"w",encoding="utf-8",newline="").write("\n".join(out)+"\n")
print("\n".join(out))
