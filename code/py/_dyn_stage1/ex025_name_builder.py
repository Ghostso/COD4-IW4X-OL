from pathlib import Path

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
rel = r"COD OL\TCLS\Tenio\TCLS.dll"
data = (ROOT / rel).read_bytes()
pe = pefile.PE(data=data, fast_load=False)
base = pe.OPTIONAL_HEADER.ImageBase


def va2off(va):
    r = va - base
    for s in pe.sections:
        if s.VirtualAddress <= r < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (r - s.VirtualAddress)
    raise ValueError(hex(va))


def imports():
    out = {}
    for ent in pe.DIRECTORY_ENTRY_IMPORT:
        for imp in ent.imports or []:
            name = imp.name.decode(errors="replace") if imp.name else ("ORD#%d" % imp.ordinal)
            out[imp.address] = (ent.dll.decode(errors="replace"), name)
    return out


imp = imports()


def show(va, n=0x120, centers=()):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    off = va2off(va)
    for ins in md.disasm(data[off:off + n], va):
        ann = ""
        if ins.mnemonic in ("call", "jmp") and "dword ptr [" in ins.op_str:
            try:
                a = int(ins.op_str.split("[")[-1].split("]")[0], 16)
                dll, name = imp.get(a, ("", ""))
                ann = " ; " + dll + "!" + name
            except Exception:
                pass
        mark = ">>" if any(abs(ins.address - c) <= 10 for c in centers) else "  "
        print(" ", mark, "%08X %-22s %-8s %s%s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, ann))


targets = [0x1003ACC6, 0x1003AE3C, 0x1003B14A, 0x1003B487, 0x1003CD12,
           0x1004177B, 0x10044130, 0x10083836, 0x100C4C38, 0x100C4CEC,
           0x100F7201, 0x100FCB31, 0x101035CD, 0x10103822, 0x10103F2D,
           0x10104182, 0x10104762]
for t in targets:
    print("\n===== %s%d XREF", hex(t))
    show(t - 0x50, 0x120, centers=(t,))

print("\n===== STRING REFS TO TCLS_SHAREDMEMEMORY")
needle = "TCLS_SHAREDMEMEMORY".encode("utf-16le")
pos = 0
while True:
    pos = data.find(needle, pos)
    if pos < 0:
        break
    r = pos
    for s in pe.sections:
        if s.PointerToRawData <= r < s.PointerToRawData + s.SizeOfRawData:
            va = base + s.VirtualAddress + (r - s.PointerToRawData)
            print("STR", hex(r), hex(va))
    pos += 1
