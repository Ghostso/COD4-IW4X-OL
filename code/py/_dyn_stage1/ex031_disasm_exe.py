from pathlib import Path

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
p = ROOT / r"COD OL\codoMP_client_shipRetail.exe"
data = p.read_bytes()
pe = pefile.PE(data=data, fast_load=False)
base = pe.OPTIONAL_HEADER.ImageBase


def va2off(va):
    r = va - base
    for s in pe.sections:
        if s.VirtualAddress <= r < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (r - s.VirtualAddress)
    raise ValueError(hex(va))


def section(va):
    r = va - base
    for s in pe.sections:
        if s.VirtualAddress <= r < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.Name.rstrip(b"\0").decode(errors="replace")
    return "?"


print("FILE", p)
print("AREA 0x37F60C - 0x37F900 section", section(0x37F60C))
start = base + 0x37F60C
off = va2off(start)
blob = data[off:off + 0x300]
md = Cs(CS_ARCH_X86, CS_MODE_32)
for ins in md.disasm(blob, start):
    mark = ">>" if ins.address == base + 0x37F70C else "  "
    print(" ", mark, "%08X %-22s %-8s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))

print("\nPTR CONTEXT at 0x37F70C")
o = va2off(base + 0x37F70C)
print("bytes", data[o - 16:o + 16].hex())
print("dword", hex(int.from_bytes(data[o:o + 4], "little")))

print("\nNEAR STRINGS")
for target in [0x9DBF80, 0x9DB3C4]:
    print("target", hex(target))
    for off2 in range(0, len(data) - 4):
        if int.from_bytes(data[off2:off2 + 4], "little") == target:
            try:
                va = base + pe.get_rva_from_offset(off2)
            except Exception:
                continue
            if abs(va - (base + 0x37F70C)) < 0x1000:
                print("  near ptr", hex(va), section(va))
