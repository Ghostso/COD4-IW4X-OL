# -*- coding: utf-8 -*-
"""045: PE structure of all three samples + the decisive 0x87BE00 disasm (VA form)."""
import sys, json, hashlib, struct
sys.stdout.reconfigure(encoding="utf-8")
import pefile, capstone
WS=r"D:\BaiduNetdiskDownload\使命召唤OL"
IMG=WS+r"\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
EXE=WS+r"\COD OL\codoMP_client_shipRetail.exe"
DLL=WS+r"\COD OL\codoMP_client_shipRetailBase.dll"
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()
print("=== sample identity (full SHA-256) ===")
for lab,p in (("S-IMG",IMG),("S-EXE",EXE),("S-DLL",DLL)):
    import os
    print("  %-6s %s  %s bytes"%(lab, sha(p), os.path.getsize(p)))
print()
for lab,p in (("S-IMG",IMG),("S-EXE",EXE),("S-DLL",DLL)):
    pe=pefile.PE(p,fast_load=True)
    oh=pe.OPTIONAL_HEADER
    print("=== %s %s ==="%(lab,p))
    print("   Machine=%04X ImageBase=%08X SizeOfImage=%08X EP=%08X TimeDateStamp=%08X"%(pe.FILE_HEADER.Machine,oh.ImageBase,oh.SizeOfImage,oh.AddressOfEntryPoint,pe.FILE_HEADER.TimeDateStamp))
    print("   FileAlignment=%X SectionAlignment=%X"%(oh.FileAlignment,oh.SectionAlignment))
    for s in pe.sections:
        print("   sec %-8s VA=%08X VSize=%08X Raw=%08X RSize=%08X Char=%08X"%(s.Name.rstrip(b"\x00").decode("latin1"),s.VirtualAddress,s.Misc_VirtualSize,s.PointerToRawData,s.SizeOfRawData,s.Characteristics))
    d=oh.DATA_DIRECTORY
    print("   IMPORT dir RVA=%08X size=%X ; IAT dir RVA=%08X size=%X"%(d[1].VirtualAddress,d[1].Size,d[12].VirtualAddress,d[12].Size))
    print()
print("=== 0x87BE00 primitive FULL disasm (RVA space) ===")
b=open(IMG,"rb").read(); IB=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)
for ins in md.disasm(b[0x87be00:0x87bf50], IB+0x87be00):
    tag=""
    if "0xca84e8" in ins.op_str: tag="   ; SELECT (ws2_32 ord 18)"
    elif "0xca84e4" in ins.op_str: tag="   ; recv (ws2_32 ord 16)"
    elif "0xca853c" in ins.op_str: tag="   ; WSAGetLastError (ord 111)"
    print("  %08X  %-18s %s %s%s"%(ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, tag))
