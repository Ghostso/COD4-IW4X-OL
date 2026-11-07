import sys
from pathlib import Path
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
COD = ROOT / "COD OL"


def load(name):
    pe = pefile.PE(str(COD / name), fast_load=False)
    data = (COD / name).read_bytes()
    return pe, data


def off(pe, rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + rva - s.VirtualAddress
    return None


def dis(data, pe, rva, n, base):
    o = off(pe, rva)
    if o is None:
        print("NO OFF", hex(rva))
        return
    print(f"-- {rva:#x} off {o:#x} va {base + rva:#x}")
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    for ins in md.disasm(data[o : o + n], base + rva):
        note = ""
        if ins.mnemonic in ("call", "jmp"):
            for op in ins.operands:
                if op.type == 3 and op.mem.base == 0 and op.mem.index == 0:
                    note = f" ; MEM {op.mem.disp:#x}"
        print(f"{ins.address:08X} {ins.bytes.hex():<22} {ins.mnemonic:<8} {ins.op_str}{note}")


exe_pe, exe_data = load("codoMP_client_shipRetail.exe")
base_pe, base_data = load("codoMP_client_shipRetailBase.dll")
print("EXE entry", hex(exe_pe.OPTIONAL_HEADER.AddressOfEntryPoint))
print("BASE entry", hex(base_pe.OPTIONAL_HEADER.AddressOfEntryPoint))
dis(exe_data, exe_pe, exe_pe.OPTIONAL_HEADER.AddressOfEntryPoint, 0x200, exe_pe.OPTIONAL_HEADER.ImageBase)
dis(base_data, base_pe, base_pe.OPTIONAL_HEADER.AddressOfEntryPoint, 0x180, base_pe.OPTIONAL_HEADER.ImageBase)
print("\nBASE exports")
for s in base_pe.DIRECTORY_ENTRY_EXPORT.symbols:
    print("ord", s.ordinal, "rva", hex(s.address), "va", hex(base_pe.OPTIONAL_HEADER.ImageBase + s.address))
    dis(base_data, base_pe, s.address, 0x180, base_pe.OPTIONAL_HEADER.ImageBase)
